from array import array

from logging import getLogger; log = getLogger("minty.histograms.manager")

import ROOT as R


AXES_GETTERS = [R.TH1.GetXaxis, R.TH1.GetYaxis, R.TH1.GetZaxis]

def make_sparse_hist_filler(hist):
    dimensions = hist.GetNdimensions()
    def filler(*args, **kwargs):
        w = kwargs.pop("w", 1)
        assert len(args) == dimensions, "Filling THnSparse with wrong number of arguments"
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
            
    hist = TH(name, title, *binning_args)
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

    hist = R.THnSparseF(name, title, dimensions, 
                        nbins, xmins, xmaxs)
                        
    for i, binning in fixup_axes:
        hist.GetAxis(i).Set(len(binning)-1, array("d", binning))
    
    filler = make_sparse_hist_filler(hist)
    return hist, filler

class HistogramManager(object):
    def __init__(self, resultname):
        self.histo_store = {}
        self.filler_store = {}
        self.resultname = resultname
        
        # When histograms are created, don't put them 
        # in the current ROOT directory
        R.TH1.AddDirectory(False)
    
    def finalize(self):
        self.save()

    def save(self):
        """
        Write histograms in name order.
        """
        nameshistos = [(h.GetName(), h) for h in self.histo_store.values()]
        for name, histogram in sorted(nameshistos):
            histogram.Write()

    def build_histogram(self, *hname, **kwargs):
        """
        Create a histogram.
        """
        
        name =  [element for element in expand_hname(*hname) if element != "*"]
        name = "_".join(name)
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
                
        self.histo_store[hname] = hist
        self.filler_store[hname] = filler
        return filler

    def get(self, *hname, **kwargs):
        """
        Retrieve the histogram filler function from the manager.
        The positional arguments fed (`hname`) are flattened and joined with '_'
        `kwargs` must specify at least the binning with the `b` parameter.
        """
        if hname in self.filler_store:
            return self.filler_store[hname]
        return self.build_histogram(*hname, **kwargs)
