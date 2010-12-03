from sys import argv

import ROOT as R

from IPython.Shell import IPShellEmbed; ip = IPShellEmbed(["-pdb"])

def main():

    f = R.TFile(argv[1])
    ip()
