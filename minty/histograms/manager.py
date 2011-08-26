from collections import defaultdict
from cPickle import dumps


from logging import getLogger; log = getLogger("minty.histograms.manager")

import ROOT as R

from .builders import build_histogram_auto

    
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
        to_rewrite = []
        for fullname, (obj, name, subdir) in self.store.iteritems():
            if isinstance(obj, dict):
                log.error("I am rewriting {0}".format(name))
                to_rewrite.append(fullname)
                
        for fullname in to_rewrite:
            self.write_object(fullname, self[fullname])
                
        self.save()
        self.file.Close()

    def save(self):
        """
        Write objects in name order.
        """
        log.info("Writing to %s", self.filename)
        for obj, name, subdir in sorted(self.store.values(), key=lambda (a, b, c): c):
            if subdir:
                self.file.Get("/".join(subdir)).WriteObject(obj, name, "")
            else:
                self.file.WriteObject(obj, name, "")

    def write_object(self, name, what):
        self[name] = R.TObjString(dumps(what))

    def write_parameter(self, name, value):
        self[name] = R.TParameter(type(value))(name, value)

    def expand_hname(self, hname):
        name =  [element for element in expand_hname(*hname) if element != "*"]
        return "/".join(name)

    def build_histogram(self, *hname, **kwargs):
        """
        Create a histogram.
        """
        name = self.expand_hname(hname)
        
        title = kwargs.pop("t", name) # title defaults to name
        if not "b" in kwargs:
            raise RuntimeError("Please specify binning "
                                  "(`b=` in HistogramManager.get)")
        binning = kwargs.pop("b")
        assert not kwargs, "Unrecognized arguments to build_histogram: %r" % kwargs
    
        hist, filler = build_histogram_auto(name, title, binning)
                
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
        asdict = kwargs.pop("asdict", False)
        if asdict:
            name = self.expand_hname(hname)
            d = defaultdict(int)
            self[name] = self.hist_store[hname] = d 
            def filler(x):
                d[x] += 1
            self.filler_store[hname] = filler
            return filler
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


if __name__ == "__main__":
    
    hm = HistogramManager("test.root")
    hm.write_object("test_set", set("abcd"))
    hm.write_object("test_list", ["abcd"])
    hm.write_object("test_str", "abcd")
    hm.finalize()
    
