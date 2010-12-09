
from __future__ import division

import ROOT as R
from array import array

from manager import HistogramManager, AthenaHistogramManager

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
    if "[MeV]" in orig_hist.GetXaxis().GetTitle():
        hist = histaxes_mev_to_gev(orig_hist)
        hist = meaningful_yaxis(hist)
    else:
        hist = orig_hist
    return hist

unit_re = re.compile(r"(\[[^\]]+\])")
def meaningful_yaxis(orig_hist):
    hist = orig_hist.Clone()
    x_title = orig_hist.GetXaxis().GetTitle()
    y_title = orig_hist.GetYaxis().GetTitle()
    if not y_title:
        y_title = "N"
    x_units = unit_re.search(x_title)
    if not x_units: return hist
    assert x_units, "Couldn't find unit on x-axis: %s" % x_title
    xunit = x_units.groups()[0]
    if xunit not in hist.GetYaxis().GetTitle():
        hist.Scale(1, "width")
        hist.GetYaxis().SetTitle("%s / %s" % (y_title, xunit))
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
    
def get_bin_positions(axis):
    bins = axis.GetXbins()
    if bins.fN:
        return [bins[i] for i in xrange(bins.fN)]
    xn, xmin, xmax = axis.GetNbins(), axis.GetXmin(), axis.GetXmax()
    bwidth = (xmax - xmin) / xn
    return [xmin + bwidth*i for i in xrange(xn)] + [xmax]
    
def scale_axis(axis, scale):
    bins = get_bin_positions(axis)
    new_bins = array("d", (bin*scale for bin in bins))
    axis.Set(axis.GetNbins(), new_bins)

def normalize_by_axis(orig_hist, xaxis=True):
    """
    Normalise rows or columns of a 2D histogram
    xaxis = True => normalize Y bins in each X bin to the sum of the X bin.
    """
    hist = orig_hist.Clone()
    
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
        
    return hist
    
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
    coord = array("i", [0] * hist.GetNdimensions())
    for i in xrange(hist.GetNbins()):
        value = hist.GetBinContent(i, coord)
        yield tuple(coord), value

