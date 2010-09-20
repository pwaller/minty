
from __future__ import division

import ROOT as R
from array import array

from manager import HistogramManager

import re

def mirror_bins(bins):
    """
    Given eta bins (0, 1, 2), return (-2, -1, 0, 1, 2)
    """
    assert bins[0] == "var"
    bins = bins[1:] # remove "var"
    return ("var",) + tuple(map(float.__neg__, reversed(bins[1:]))) + bins

def double_bins(bins, doublings=1):
    """
    Given pt bins (15, 20, 30), return (15, 17.5, 20, 25, 30)
    """
    assert bins[0] == "var"
    bins = bins[1:] # remove "var"
    
    for i in xrange(doublings):
        result = []
        for i, (this, next) in enumerate(zip(bins, bins[1:])):
            if i == 0:
                result.append(this)
            result.append(this + (next-this)/2)
            result.append(next)
        bins = result
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
    
def thnsparse_iterator(hist):
    coord = array("i", [0] * hist.GetDimension())
    for i in xrange(hist.GetNbins()):
        value = hist.GetBinContent(i, coord)
        yield tuple(coord), value

