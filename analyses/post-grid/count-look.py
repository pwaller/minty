#! /usr/bin/env python

from IPython.Shell import IPShellEmbed; ip = IPShellEmbed()

import ROOT as R

import minty
from minty.histograms.cuts_histogram import make_cut_histogram

def count_look(filename):
    f = R.TFile(filename)
    cuthist = make_cut_histogram(f.photon_counts)
    
    
    ip()

if __name__ == "__main__":
    from sys import argv
    count_look(argv[1])
