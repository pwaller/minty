from array import array

from logging import getLogger; log = getLogger("minty.histograms.manager")

import ROOT as R


def make_sparse_hist_filler(hist):
    dimensions = hist.GetNdimensions()
    def filler(*args, **kwargs):
        w = kwargs.pop("w", 1)
        assert len(args) == dimensions, "Filling THnSparse with wrong number of arguments (%i instead of %i)" % (len(args), dimensions)
        hist.Fill(array('d', args), w)
    return filler
    
def expand_hname(*hname):
    result = []
    for element in hname:
        if isinstance(element, tuple):
            result.extend(expand_hname(*element))
        elif element:
            # Empty elements are not included!
            if "*" in result:
                pos = (i for i, v in reversed(list(enumerate(result))) if v == "*").next()
                result.insert(pos+1, str(element))
            else:
                result.append(str(element))
    
    return result

def build_histogram_plain(name, title, binning):
    """
    Build a histogram inheriting the TH1.
    
    `binning` should be a list of tuples, describing the bins for each axis.
    """
    dimensions = len(binning)
    TH = {1: R.TH1F, 2: R.TH2F, 3: R.TH3F}[dimensions]
    binning_args, fixup_axes = [], []
    
    AXES_GETTERS = [R.TH1.GetXaxis, R.TH1.GetYaxis, R.TH1.GetZaxis]
    for bins, axis_getter in zip(binning, AXES_GETTERS):
        if len(bins) == 3:
            binning_args.extend(bins)
        elif bins[0] == "var":
            variable_bins = bins[1:]
            dummy_bins = (len(variable_bins), 
                          variable_bins[0], 
                          variable_bins[-1])
            binning_args.extend(dummy_bins)
            fixup_axes.append((axis_getter, variable_bins))
        
        else:
            raise RuntimeError("A given set of bins should either be "
                "three long, or the first element must be 'var' to "
                "indicate variable binning")
    
    hname = name.split("/")[-1] # remove path from name
    hist = TH(hname, title, *binning_args)
    for fixup_axis, binning in fixup_axes:
        fixup_axis(hist).Set(len(binning)-1, array("d", binning))
        
    filler = hist.Fill
    return hist, filler
    
def build_histogram_sparse(name, title, binning):
    """
    Build a THnSparse
    """
    dimensions = len(binning)
    nbins, xmins, xmaxs = array("i", []), array("d", []), array("d", [])
    fixup_axes = []
    
    for i, bins in enumerate(binning):
        if len(bins) == 3:
            nbins.append(bins[0])
            xmins.append(bins[1])
            xmaxs.append(bins[2])
            
        elif bins[0] == "var":
            variable_bins = bins[1:]
            nbins.append(len(variable_bins))
            xmins.append(variable_bins[0])
            xmaxs.append(variable_bins[-1])
            fixup_axes.append((i, variable_bins))
        else:
            raise RuntimeError("A given set of bins should either be "
                "three long, or the first element must be 'var'")

    hname = name.split("/")[-1] # remove path from name
    hist = R.THnSparseF(hname, title, dimensions, 
                        nbins, xmins, xmaxs)
                        
    for i, binning in fixup_axes:
        hist.GetAxis(i).Set(len(binning)-1, array("d", binning))
    
    filler = make_sparse_hist_filler(hist)
    return hist, filler

class HistogramManager(object):
    def __init__(self, filename):
        # Required to prevent ROOT from complaining about multiple histograms
        # with the same name.
        R.TH1.AddDirectory(False)

        self.store = {}
        self.hist_store = {}
        self.filler_store = {}
        self.filename = filename
        
        # When histograms are created, don't put them 
        # in the current ROOT directory
        self.file = R.TFile(filename, "RECREATE")
        #R.TH1.AddDirectory(False)

    def __setitem__(self, key, value):
        self.file.cd("/")
        def mkdirs(d, subdirs):
            if not subdirs:
                return d
            sd, rem = subdirs[0], subdirs[1:]
            if not d.Get(sd):
                d.mkdir(sd)
            return mkdirs(d.Get(sd), rem)

        subdir = key.split("/")
        name = subdir.pop()
        d = mkdirs(self.file, subdir)
        d.cd()    
        if hasattr(value, "SetDirectory"):
            value.SetDirectory(d)
        self.store[key] = (value, name, subdir)

    def __getitem__(self, key):
        return self.store[key][0]
    
    def finalize(self):
        self.save()
        self.file.Close()

    def save(self):
        """
        Write objects in name order.
        """
        for obj, name, subdir in sorted(self.store.values(), key=lambda (a, b, c): c):
            if subdir:
                self.file.Get("/".join(subdir)).WriteObject(obj, name, "")
            else:
                self.file.WriteObject(obj, name, "")

    def write_parameter(self, name, value):
        self[name] = R.TParameter(type(value))(name, value)

    def build_histogram(self, *hname, **kwargs):
        """
        Create a histogram.
        """
        
        name =  [element for element in expand_hname(*hname) if element != "*"]
        name = "/".join(name)
        title = kwargs.pop("t", name) # title defaults to name
        if not "b" in kwargs:
            raise RuntimeError("Please specify binning "
                                  "(`b=` in HistogramManager.get)")
        binning = kwargs.pop("b")
        assert not kwargs, "Unrecognized arguments to build_histogram: %r" % kwargs
    
        dimensions = len(binning)
        
        if dimensions <= 3:
            hist, filler = build_histogram_plain(name, title, binning)
        else:
            hist, filler = build_histogram_sparse(name, title, binning)
                
        self[name] = hist
        self.hist_store[hname] = hist
        self.filler_store[hname] = filler
        return filler

    def geth(self, *hname):
        return self.hist_store[hname]

    def get(self, *hname, **kwargs):
        """
        Retrieve the histogram filler function from the manager.
        The positional arguments fed (`hname`) are flattened and joined with '_'
        `kwargs` must specify at least the binning with the `b` parameter.
        """
        if hname in self.filler_store:
            return self.filler_store[hname]
        return self.build_histogram(*hname, **kwargs)


class AthenaHistogramManager(HistogramManager):

    def __init__(self, resultname):
        super(AthenaHistogramManager, self).__init__(resultname)
        # Set up Minty histogram and ntuple service
        from AthenaCommon import CfgMgr
        from AthenaCommon.AppMgr import ServiceMgr
        if not hasattr(ServiceMgr, 'MintyHistogramSvc'):
            hsvc = CfgMgr.THistSvc("MintyHistogramSvc")
            hsvc.Output += [ "minty DATAFILE='MINTY.root' TYP='ROOT' OPT='RECREATE'" ]
            hsvc.PrintAll = False
            ServiceMgr += hsvc
        self._hsvc = None 

    @property
    def hsvc(self):
        from AthenaPython import PyAthena
        if self._hsvc:
            return self._hsvc
        else:
            return PyAthena.py_svc('THistSvc/MintyHistogramSvc')


    def save(self):
        nameshistos = [(h.GetName(), h) for h in self.histo_store.values()]
        for name, histogram in sorted(nameshistos):
            self.hsvc["/".join(("minty",self.resultname, name))] = histogram


        
