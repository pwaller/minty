"""
A cuts histogram is one which encodes information about correlations between all 
cuts simultaneously.
"""

import ROOT as R

R.THnSparse.GetDimension = R.THnSparse.GetNdimensions

def TH1__GetAxis(self, i):
    assert i <= 3
    return [R.TH1.GetXaxis, R.TH1.GetYaxis, R.TH1.GetZaxis][i](self)
R.TH1.GetAxis = TH1__GetAxis

from array import array
from sys import stdout
from itertools import izip_longest
from os import listdir

class CutAxis(object):
    def __init__(self, cuthisto, *titles):
        #print "New cutaxis:", cuthisto, titles
        self.cuthisto = cuthisto
        self.titles = titles
        self._projected = None
    
    @property
    def projected(self):
        if not self._projected:
            self._projected = self.cuthisto.project(*self.idxs)
        return self._projected

    @property
    def title(self):
        return "+".join(self.titles)

    def __getitem__(self, args):
        return self.projected[self.find_bin(*args)]

    def find_bin(self, *values):
        h = self.projected.hist
        
        #return h.GetBin(array("i", values))
        if len(self.titles) > 3:
            return h.GetBin(array("d", values))
        else:
            return h.FindBin(*values)

    def project_out(self, *slices):
        """
        Remove this axis from the target histogram
        
        If `slices` is not specified, take the "True"*Ndims bin
        """
        # Keep track of previous axis states before projection
        set_axes = [] 
        if not slices:
            slices = (1,) * len(self.axes)
        
        for slice, axis in izip_longest(slices, self.axes):
            if isinstance(slice, (int, long)):
                bin = axis.FindBin(slice)
                bin_range = bin, bin
            elif isinstance(slice, tuple):
                lo, hi = slice
                bin_range = axis.FindBin(lo), axis.FindBin(hi)
            elif slice is None:
                bin_range = None
            else:
                assert False, "Invalid slice"
            
            if bin_range:
                prev_set = axis.TestBit(R.TAxis.kAxisRange)
                prev_range = axis.GetFirst(), axis.GetLast()
                set_axes.append((axis, prev_set, prev_range))
                axis.SetRange(*bin_range)
                #axis.SetBit(R.TAxis.kAxisRange)
            
        idxs = set(self.idxs)
        axes = [i for i in xrange(self.cuthisto.hist.GetDimension()) 
                if i not in idxs]
        result = self.cuthisto.project(*axes)
        for axis, axis_range_bit, prev_range in set_axes:
            axis.SetRange(*prev_range)
            axis.SetBit(R.TAxis.kAxisRange, axis_range_bit) 
        return result
    
    @property
    def axes(self):
        return map(self.cuthisto.axis, self.titles)
        
    @property
    def axes_objs(self):
        return [self.cuthisto(axis) for axis in self.titles]
    
    @property
    def idxs(self):
        #print self.titles
        return map(self.cuthisto.axis_idx, self.titles)
    
    def value(self, *position): 
        return self.find_bin(*position)
    
    @property
    def true(self):
        return self.projected[self.find_bin(*(True,)*len(self.titles))]

    @property
    def true_unweighted(self):
        return self.projected.hist.GetBinError(self.find_bin(*(True,)*len(self.titles)))**2
        
    @property
    def false(self):
        return self.projected[self.find_bin(*(False,)*len(self.titles))]
    
    @property
    def total(self):
        return self.true + self.false
    
    def __repr__(self):
        args = self.titles, self.false, self.true
        return "<CutAxis %s false=%i true=%i>" % args
        
    def __and__(self, rhs):
        return CutAxis(self.cuthisto, *(self.titles + rhs.titles))
        
def make_cut_histogram(hist, axestitles=None):
    class CutHistogram_Specific(CutHistogram):
        pass
    
    if isinstance(hist, R.TH1):
        CutHistogram_Specific.__getitem__ = lambda self, i: hist[i]
    
    if axestitles:
        assert len(axestitles) == hist.GetDimension()
        for i, axistitle in enumerate(axestitles):
            hist.GetAxis(i).SetTitle(axistitle)
    
    axis_idxs = {}
    axes = []
    for i in xrange(hist.GetDimension()):
        title = hist.GetAxis(i).GetTitle()
        get_cutaxis = lambda self, n=title: self(n)
        setattr(CutHistogram_Specific, title, property(get_cutaxis))
        axes.append(title)
        axis_idxs[title] = i
        #print title, i

    return CutHistogram_Specific(hist, axes, axis_idxs)
    
class CutHistogram(object):
    def __init__(self, hist, axes, axis_idxs):
        self.hist = hist
        self.axes = axes
        self.axis_idxs = axis_idxs 
    
    def __call__(self, *what):
        return CutAxis(self, *what)
    
    @property
    def axes_objs(self):
        return [self(i) for i in self.axes]
    
    def axis_idx(self, title):
        return self.axis_idxs[title]
    
    def axis(self, title):
        return self.hist.GetAxis(self.axis_idx(title))
    
    def __getitem__(self, what):
        return self.hist.GetBinContent(what)
        
    def project(self, *axes):
        if len(self.axes) == 1:
            return make_cut_histogram(self.hist)
        assert len(axes) < len(self.axes)
        #print "Projecting axes:", axes, [self.hist.GetAxis(i).GetTitle() for i in axes]
        
        if len(self.axes) == 3:
            new_h = self.hist.Project3D("".join("xyz"[i] for i in axes))
            new_h.SetDirectory(None)
        elif len(self.axes) == 2:
            assert len(axes) == 1
            do_proj = [self.hist.ProjectionX, self.hist.ProjectionY][axes[0]]
            new_h = do_proj()
            new_h.SetDirectory(None)
        elif len(axes) <= 3:
            new_h = self.hist.Projection(*axes)
            new_h.SetDirectory(None)
        else:
            new_h = self.hist.Projection(len(axes), array("i", axes))
        
        #print "Projected:", new_h, new_h.GetName()
        #R.gDirectory.ls()
        return make_cut_histogram(new_h)
