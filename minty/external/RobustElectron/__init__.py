from os.path import abspath, dirname
from ROOT import gROOT

this_directory = dirname(abspath(__file__))
gROOT.LoadMacro("%s/robustIsEMDefs.C+" % this_directory)
from ROOT import isRobustLoose, isRobustMedium, isRobusterTight

