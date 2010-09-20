
from __future__ import division

import ROOT as R
from array import array
from ctypes import POINTER, c_double

import re

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

def fixup_hist_units(orig_hist):
    hist = histaxes_mev_to_gev(orig_hist)
    hist = meaningful_yaxis(hist)
    return hist

unit_re = re.compile(r"(\[[^\]]+\])")
def meaningful_yaxis(orig_hist):
    hist = orig_hist.Clone()
    x_title = orig_hist.GetXaxis().GetTitle()
    y_title = orig_hist.GetYaxis().GetTitle()
    x_units = unit_re.search(x_title)
    assert x_units, "Couldn't find unit on x-axis: %s" % x_title
    hist.Scale(1, "width")
    hist.GetYaxis().SetTitle("%s / %s" % (y_title, x_units.groups()[0]))
    return hist

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
        
        # Note: this gets garbage collected if _creates is set on the funciton 
        # object (as it is in init_root)
        proj = Project("slice", bin, bin)
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
    
def thnsparse_iterator(hist):
    coord = array("i", [0] * hist.GetDimension())
    for i in xrange(hist.GetNbins()):
        value = hist.GetBinContent(i, coord)
        yield tuple(coord), value

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
        f = R.TFile(self.resultname, "recreate")
        self.save()
        f.Close()

    def save(self):
        """
        Write histograms in name order.
        """
        for name, histogram in sorted(self.histo_store.iteritems()):
            histogram.Write()

    def build_histogram(self, *hname, **kwargs):
        """
        Create a histogram.
        """
        
        name = "_".join(expand_hname(*hname))
        title = kwargs.pop("title", name) # title defaults to name
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
