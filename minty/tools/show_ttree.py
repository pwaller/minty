from sys import argv

import ROOT as R

def main():

    f = R.TFile(argv[1])
    print "\n".join(sorted(l.GetName() for l in f.PAUReco.GetListOfLeaves()))
