#! /usr/bin/env python

import ROOT as R

from bettermerge import most_recent_cycle_keys

def rescale_dir(d_in, d_out, scale):
    """
    Recursively rescale histogram objects in d_in and write them to d_out
    """
    _, keys = most_recent_cycle_keys(d_in)
    
    print "Scaling ", d_in.GetPath(), " -> ", d_out.GetPath()
    
    for key in keys:
        name, obj = key.GetName(), key.ReadObj()
        if isinstance(obj, R.TDirectory):
            new_dir = d_out.mkdir(name)
            rescale_dir(obj, new_dir, scale)
        elif isinstance(obj, (R.TH1, R.THnSparse)):
            d_out.cd()
            print "  Scaling %s" % name
            obj.Scale(scale)
            obj.Write()        

def main():
    from sys import argv
    scale = float(argv[1])
    fname_in = argv[2]
    fname_out = argv[3]
    
    f_in = R.TFile(fname_in, "read")
    f_out = R.TFile(fname_out, "recreate")
    
    rescale_dir(f_in, f_out, scale)
