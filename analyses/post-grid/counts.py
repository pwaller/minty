#! /usr/bin/env python

# Scripts expect to be run with a cwd where "minty" and "pytuple" are present.
# (Or minty and pytuple are in the path)
import os; import sys; sys.path.insert(0, os.getcwd())

from IPython.Shell import IPShellEmbed; ip = IPShellEmbed(["-pdb"])

from minty.histograms.cuts_histogram import make_cut_histogram
import ROOT as R

from os.path import basename
from array import array

def get_cut_stats(axis):
   # print "%12s" % axis.title, "total=%6i" % axis.true,
    proj = axis.project_out(True)
    
    numbers = [axis.true]
    
    counts = []
    for ax in ["grl", "pv", "g10_loose", "oq"]:
        value = proj(ax).true
        numbers.append(value)
        counts.append("%s=%6i" % (ax, value))

    #p = proj
    #numbers.append((p.grl & p.pv & p.g10_loose & p.oq).true)
    
    #"""
    combined = ["grl"]
    #combined_axis = p("grl")
    for axis in ["g10_loose", "pv", "oq"]:
        combined.append(axis)
        combined_axis = proj(*combined)
        #combined_axis &= p(axis)
        numbers.append(combined_axis.true)
        #counts.append("%s=%6i" % (combined_axis.title, combined_axis.true))
        #print combined_axis
    #"""
    
    #print " ".join(counts)
    return map(int, numbers)

def print_hist(orig_h):
    h_all = make_cut_histogram(orig_h)
    h = h_all.fiducial.project_out()
    """
    #good = h_all.fiducial & h_all.grl
    #print good, good.project_out().loose, h_all.loose
    #h = good.project_out()
    h = good = h_all("fiducial", "grl2", "g10_loose", "oq", "pv")
    n_all = good.true
    h = h.project_out()
    if not n_all: return None
    #h = h.grl2.project_out(True)
    #print 
    return (map(int, [h.loose.true, h.tight.true, h.robust_tight.true]),)
    """
    return (
        #get_cut_stats(h_all.fiducial),
        ["loose   "]    + get_cut_stats(h.loose),
        ["tight   "]    + get_cut_stats(h.tight),
        ["RobustTight"] + get_cut_stats(h.robust_tight),
    )
    
def inject_run(run, stuff):
    if not stuff:
        return []
    result = []
    for i, line in enumerate(stuff):
        if not i:
            result.append([run] + line)
        else:
            result.append(["^  "] + line)
    return result

lengths = " |  152214 |    loose    |           4 |          3 |         4 |                3 |         4 |                    3 |                       3 |                          3 |"

def main(files):
    rows = []
    hist_sum = None
    for file in files:
        #calculate_run(file)
        f = R.TFile(file)
        run = int(basename(file).split(".")[0])
        h = f.photon_counts
        if hist_sum is None:
            hist_sum = h.Clone()
        else:
            hist_sum.Add(h)
        rows.extend(inject_run(run, print_hist(h)))
    
    rows.extend(inject_run("total", print_hist(hist_sum)))
    lens = map(lambda x: len(x)-2, lengths.split("|"))[1:]
    #lens = [7]*10
    for row in rows:
        print " |", " | ".join("{0:>{l}}".format(col, l=l) for col, l in zip(row, lens)), "|"
        
 
if __name__ == "__main__":
    from sys import argv
    main(argv[1:])
#test_run("result/160980.root")
#test_run("new.root")
