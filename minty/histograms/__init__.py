
from __future__ import division

import ROOT as R
from array import array
from ctypes import POINTER, c_double
NULL_DOUBLEPTR = POINTER(c_double)()
NULL_DOUBLEPTR.typecode = "d"
NULL_DOUBLEPTR.itemsize = 8

MAX_STORE_SIZE = 10000
EMPTY_WEIGHTS = array("d", [1]*(MAX_STORE_SIZE+3))

def expand_hname(*hname):
    result = []
    for element in hname:
        if isinstance(element, tuple):
            result.extend(expand_hname(*element))
        elif element:
            # Empty elements are not included!
            result.append(str(element))
        
    return result

def mirror_bins(bins):
    """
    Given eta bins (0, 1, 2), return (-2, -1, 0, 1, 2)
    """
    assert bins[0] == "var"
    bins = bins[1:] # remove "var"
    return ("var",) + tuple(map(float.__neg__, reversed(bins[1:]))) + bins

def double_bins(bins):
    """
    Given pt bins (15, 20, 30), return (15, 17.5, 20, 25, 30)
    """
    assert bins[0] == "var"
    bins = bins[1:] # remove "var"
    result = []
    for i, (this, next) in enumerate(zip(bins, bins[1:])):
        if i == 0:
            result.append(this)
        result.append(this + (next-this)/2)
        result.append(next)
    return ("var",) + tuple(result)

def scale_bins(bins, factor):
    """
    Scale bins by a factor
    """
    assert bins[0] == "var"
    bins = bins[1:] # remove "var"
    def scale(n): return n * factor
    return ("var",) + tuple(map(scale, bins))

def histaxes_mev_to_gev(orig_hist):
    """
    If an axis contains "[MeV]" in its title, rescale it to GeV and 
    update the title.
    """
    hist = orig_hist.Clone()
    for axis in (hist.GetXaxis(), hist.GetYaxis()):
        if "[MeV]" in axis.GetTitle():
            axis.SetTitle(axis.GetTitle().replace("[MeV]", "[GeV]"))
            scale_axis(axis, 1e-3)
            
    return hist
    
def scale_axis(axis, scale):
    bins = axis.GetXbins()
    new_bins = array("d", (bins[i]*scale for i in xrange(axis.GetNbins()+1)))
    axis.Set(axis.GetNbins(), new_bins)

def normalize_by_axis(hist, xaxis=True):
    """
    Normalise rows or columns of a 2D histogram
    xaxis = True => normalize Y bins in each X bin to the sum of the X bin.
    """
    if xaxis:
        Project, axis = hist.ProjectionY, hist.GetXaxis()
    else:
        Project, axis = hist.ProjectionX, hist.GetYaxis()
    
    for bin in xrange(0, axis.GetNbins() + 2):
        
        proj = Project("_slice", bin, bin)
        integral = proj.Integral()
        if integral:
            proj.Scale(1. / integral)
        
        # Insert slice
        insert_slice(proj, hist, bin, not xaxis)
    
def insert_slice(hist, into, slice_bin, xaxis=True):
    """
    Insert a 1D histogram `hist` into a row or column of a 2D histogram `into`
    """
    if xaxis:
        for bin in xrange(0, hist.GetNbinsX() + 2):
            into.SetBinContent(bin, slice_bin, hist.GetBinContent(bin))
            
    else:
        for bin in xrange(0, hist.GetNbinsX() + 2):
            into.SetBinContent(slice_bin, bin, hist.GetBinContent(bin))

AXES_GETTERS = [R.TH1.GetXaxis, R.TH1.GetYaxis, R.TH1.GetZaxis]

def make_sparse_hist_filler(hist):
    dimensions = hist.GetNdimensions()
    def filler(*args, **kwargs):
        w = kwargs.pop("w", 1)
        assert len(args) == dimensions, "Filling THnSparse with wrong number of arguments"
        hist.Fill(array('d', args), w)
    return filler

class HistogramManager(object):
    def __init__(self):
        self.histo_store = {}
        self.filler_store = {}
    
    def finalize(self):
        f = R.TFile("output.root", "recreate")
        self.save()
        f.Close()

    def save(self):
        for histogram in self.histo_store.values():
            histogram.Write()

    def build_histogram(self, *hname, **kwargs):
        # Other default kwargs
        
        hname_str = "_".join(expand_hname(*hname))
        title = kwargs.pop("title", hname_str)
        if not "b" in kwargs:
            raise RuntimeError("Please specify binning "
                                  "(`b=` in HistogramManager.get)")
        binning = kwargs.pop("b")
        assert not kwargs, "Unrecognized arguments to build_histogram: %r" % kwargs
    
        dimensions = len(binning)
        
        if dimensions <= 3:
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
                    
            hist = TH(hname_str, title, *binning_args)
            for fixup_axis, binning in fixup_axes:
                #print "Setting axis:", fixup_axis, binning
                fixup_axis(hist).Set(len(binning)-1, array("d", binning))
                
            filler = hist.Fill
        else:        
            nbins = array("i", [])
            xmins = array("d", [])
            xmaxs = array("d", [])
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

            hist = R.THnSparseF(hname_str, title, dimensions, 
                                nbins, xmins, xmaxs)
                                
            for i, binning in fixup_axes:
                #print "Setting axis (Sp):", i, binning
                hist.GetAxis(i).Set(len(binning)-1, array("d", binning))
            
            filler = make_sparse_hist_filler(hist)
            #values = array('d', [0] * dimensions)

#        """
#        temporary_store = array("d")
#        def real_filler():
#            if not temporary_store:
#                return
#            if dimensions != 1: raise NotImplementedError
#            xs = temporary_store[::dimensions]
#            hist.FillN(len(xs), xs, EMPTY_WEIGHTS)
#            # Empty the temporary store
#            temporary_store[:] = array("d")
#            
#        def filler(*args):
#            temporary_store.extend(args)
#            #if len(temporary_store) > MAX_STORE_SIZE:
#                #real_filler()
#        """
#        self.finalization.append(real_filler)
        
        
                
        self.histo_store[hname] = hist
        self.filler_store[hname] = filler
        return filler

    def get(self, *hname, **kwargs):
        if hname in self.filler_store:
            return self.filler_store[hname]
        return self.build_histogram(*hname, **kwargs)
