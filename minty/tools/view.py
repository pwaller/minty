#! /usr/bin/env python

from ROOT import TBrowser, TFile

def main(argv):
    files = []
    for f in argv:
        f = TFile(f)
        files.append(f)
        TBrowser("", f)

    from IPython.Shell import IPShellEmbed; ip = IPShellEmbed(["-pdb"])

if __name__ == "__main__":
    from sys import argv
    raise SystemExit(main(argv))
