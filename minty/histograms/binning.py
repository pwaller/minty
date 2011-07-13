from __future__ import division

from math import log10

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
    
def log_binning(nbins, lo, hi):
    log_lo, log_hi = log10(lo), log10(hi)
    width = (log_hi-log_lo) / nbins
    return ("var",) + tuple(10**(log_lo + i*width) for i in xrange(nbins+1))
