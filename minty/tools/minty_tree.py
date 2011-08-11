#! /usr/bin/env python

from sys import argv

import ROOT as R

from minty.treedefs.egamma import egamma_wrap_tree
from IPython.Shell import IPShellEmbed; ip = IPShellEmbed(["-pdb"])

def main():

    f = R.TFile(argv[1])
    
    class options:
        release = "rel16"
        project = "data11"
    
    t = egamma_wrap_tree(f.photon, options)
    
    ip()
