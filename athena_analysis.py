#! /usr/bin/env python

# Scripts expect to be run with a cwd where "minty" and "pytuple" are present.
# (Or minty and pytuple are in the path)
import os; import sys; sys.path.insert(0, os.getcwd())
from glob import glob

from AthenaCommon.AppMgr import topSequence
from ROOT import gROOT

from minty import AnalysisAlgorithm, athena_setup, setup_pool_skim

# Set default values for testing during local running
a_local_directory = "/pclmu7_home"
if os.path.exists(a_local_directory):
    input = glob("/scratch/home_lucid/ebke/Data/data10_7TeV.00155112.*/*.root*")
    options = {}
elif not "options" in dir():
    raise RuntimeError("No options during non-local running!")

# setup athena
athena_setup(input, -1)

# do autoconfiguration of input
include ("RecExCommon/RecExCommon_topOptions.py")

# start of user Analysis definitions
#gROOT.ProcessLine(".L VtxReweighting.C++")
#gROOT.ProcessLine(".L MuonPtCorr.C++")

class MyMint(AnalysisAlgorithm):
    pass

myalg = None
accept_algs = []
for mu_algo in ["Staco", "Muid"]:
    name = "MINTY_%s" % (mu_algo)
    myalg = MyMint(name)
    myalg.muon_algo = mu_algo
    myalg.do_tree_presel = False
    myalg.do_d3pd_cut = True
    myalg.do_vtx_reweighting = True
    topSequence += myalg
    accept_algs.append(name)

if "skim" in options:
    setup_pool_skim("MintySkim.AOD.root", accept_algs)

