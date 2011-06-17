#! /usr/bin/env python
from argparse import ArgumentParser
from time import time

import ROOT as R

from minty.options import load_files

def slim_tree(in_tree, destination, variables):

    in_tree.SetBranchStatus("*", False)
    for branch in variables:
        in_tree.SetBranchStatus(branch, True)
        
    n_events = -1
    clone_option = "SortBasketsByBranch"
        

    start = time()
    f = R.TFile(destination, "recreate")
    f.cd()
    out_tree = in_tree.CloneTree(n_events, clone_option)
    ct_end = time()
    f.Write()
    f.Close()

    print "Took %.3f seconds to clone tree" % (ct_end - start)
    
    
def make_chain(tree_name, files):
    t = R.TChain(tree_name)
    for filename in files:
        t.AddFile(filename)
    return t

def load_leaflist(filename):
    """
    Load a list of leaves from a text file, one per line.
    """
    leaves = set()
    with open(filename) as fd:
        for line in (l for l in (l.strip() for l in fd) if l):
            if not line.startswith("#"):
                leaves.add(line)
                
    return sorted(leaves)

def main():

    parser = ArgumentParser(description='Process some integers.')
    A = parser.add_argument
    A('-t', '--tree-name',   help='Name of the tree')
    A('-v', '--vars-file',   help='Filename containing list of variables to keep, one per line')
    A('-o', '--output-file', help="Output root filename", default="output.root")
    A('input', nargs="+")
    
    args = parser.parse_args()

    input_tree = make_chain(args.tree_name, load_files(args.input))
    variables = load_leaflist(args.vars_file)
    
    slim_tree(input_tree, args.output_file, variables)

