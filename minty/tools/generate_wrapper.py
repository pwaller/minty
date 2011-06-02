#! /usr/bin/env python

import ROOT as R
from minty.utils import init_root

def get_leaves(treename, input_file):
    input_file = R.TFile(input_file)
    tree = input_file.Get(treename)
    assert tree, "Couldn't load input tree: '%s'" % treename
    leaves = [l.GetName() for l in tree.GetListOfLeaves()]
    input_file.Close()
    return sorted(leaves)

def by_prefix(leaves, depth=0):
    result = {}
    again = any(leaf.count("_") - depth > 1 for leaf in leaves)
    for leaf in leaves:
        prefix = leaf.split("_")[depth] if "_" in leaf else ""
        result.setdefault(prefix, []).append(leaf)
    if again:
        result = dict((prefix, by_prefix(sub_leaves, depth+1)) 
                      for prefix, sub_leaves in result.iteritems())
    return result
    
def by_prefix(leaves):
    result = []
    for leaf in leaves:
        pass
    
    return result
        

def main(options, treename, input_file):
    leaves = get_leaves(treename, input_file)
    
    lbp = by_prefix(leaves)
    
    from pprint import pprint
    pprint(lbp)
    
    return
    
    for prefix, leaves in sorted(by_prefix(leaves).iteritems()):
        print prefix
        for leaf in sorted(leaves):
            print "", leaf

if __name__ == "__main__":
    import sys
    init_root()
    from optparse import OptionParser
    from IPython.Shell import IPShellEmbed; ip = IPShellEmbed(["-pdb"])
    optparser = OptionParser()
    opts, args = optparser.parse_args(sys.argv)
    args = args[1:]
    if len(args) != 2:
        optparser.error("Please specify a treename and a root file")
    main(opts, *args)
