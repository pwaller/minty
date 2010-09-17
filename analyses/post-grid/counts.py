#! /usr/bin/env python

# Scripts expect to be run with a cwd where "minty" and "pytuple" are present.
# (Or minty and pytuple are in the path)
import os; import sys; sys.path.insert(0, os.getcwd())

from IPython.Shell import IPShellEmbed; ip = IPShellEmbed(["-pdb"])

from minty.histograms.cuts_histogram import make_cut_histogram
import ROOT as R

from array import array

def print_stats(axis):
    print "%12s" % axis.title, "total=%6i" % axis.true,
    proj = axis.project_out(True)
    
    counts = []
    for ax in ["grl", "pv", "g10_loose", "oq"]:
        counts.append("%s=%6i" % (ax, proj(ax).true))
        
    combined = ["grl"]
    for axis in ["g10_loose", "pv", "oq"]:
        combined.append(axis)
        combined_axis = proj(*combined)
        counts.append("%s=%6i" % (combined_axis.title, combined_axis.true))
        #if len(combined) == 4:ip()
        
    print " ".join(counts)
    
def hist_iterator(hist):
    coord = array("i", [0] * hist.GetDimension())
    for i in xrange(hist.GetNbins()):
        value = hist.GetBinContent(i, coord)
        yield tuple(coord), value
          
def test_run(input_file):
    
    f = R.TFile(input_file)   
    h_all = make_cut_histogram(f.photon_counts)
        
    print input_file
    
    h = h_all.fiducial.project_out(True)
    print_stats(h.loose)
    print_stats(h.tight)    
    print_stats(h.robust_tight)
    
    print "Non-fiducial photons:"
    h = h_all.fiducial.project_out(False)
    print_stats(h.loose)
    print_stats(h.tight)    
    print_stats(h.robust_tight)
    
test_run("result/160980.root")
#test_run("new.root")
