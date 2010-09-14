#! /usr/bin/env python

if __name__ == "__main__":
    # Scripts expect to be run with a cwd where "minty" and "pytuple" exist.
    # (Or minty and pytuple are in the path)
    import os; import sys; sys.path.insert(0, os.getcwd())

import minty
from minty.treedefs.egamma import egamma_wrap_tree
import ROOT as R

def test_ev(idx, ev):
    ev.RunNumber, ev.LumiBlock, ev.EventNumber, ev.EF.g10_loose, [v.nTracks for v in ev.vertices]
    
    for obj in ev.photons:
        obj.pt, obj.cl.pt, obj.true.pt, obj.true.matched, obj.loose, obj.tight
        
    for obj in ev.electrons:
        obj.pt, obj.cl.pt, obj.true.pt, obj.true.matched, obj.loose, obj.tight

def make_chain(treename, files):
    t = R.TChain(treename)
    for f in files:
        t.Add(f)
    return t

def main():
    minty.init_root()

    from time import time
    
    start = time()
    tt = egamma_wrap_tree(make_chain("PAUReco", ["example-pau.root"]))
    nev = tt.loop(test_ev)
    elapsed = time() - start
    print "Took %.2f seconds to process %i events (%.2f/sec)" % (elapsed, nev, nev/elapsed)
           
    start = time()
    tt = egamma_wrap_tree(make_chain("egamma", ["example-egamma.root"]))
    nev = tt.loop(test_ev)
    elapsed = time() - start
    print "Took %.2f seconds to process %i events (%.2f/sec)" % (elapsed, nev, nev/elapsed)

if __name__ == "__main__":
    from IPython.Shell import IPShellEmbed; IPShellEmbed(["-pdb"])
    main()
