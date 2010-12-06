#! /usr/bin/env python

# Scripts expect to be run with a cwd where "minty" and "pytuple" are present.
# (Or minty and pytuple are in the path)
import os; import sys; sys.path.insert(0, os.getcwd())
from glob import glob
from bisect import bisect
from cPickle import load
from math import sin, atan, atan2, exp

from AthenaCommon.AppMgr import topSequence
from ROOT import gROOT

from minty import AnalysisAlgorithm, athena_setup, setup_pool_skim
from minty.utils import CutGroup, Cut, SetContainer, Histo, event_cache

MZ = 91.1876*GeV

def getTP(obj):
    if hasattr(obj, "trackParticle"):
        return obj.trackParticle()
    elif obj.hasCombinedMuonTrackParticle():
        return obj.combinedMuonTrackParticle()
    else:
        return obj.track()

def getIDTP(obj):
    if hasattr(obj, "trackParticle"):
        return obj.trackParticle()
    elif obj.hasInDetTrackParticle():
        return obj.inDetTrackParticle()
    else:
        return obj.track()


def theta_from_eta(eta):
    #eta= -log tan (theta/2)
    if eta < -200: 
        eta = -200
    theta = 2*atan(exp(- eta))
    return theta

# run to period mapping
run_to_period =  {
    "MC" : (     0,152165),
    "A"  : (152166,153200),
    "B"  : (153565,155160),
    "C"  : (155228,156682),
    "D"  : (158045,159224),
    "E1" : (160387,160479),
    "E2" : (160530,160530),
    "E3" : (160613,160879),
    "E4" : (160899,160980),
    "E5" : (161118,161379),
    "E6" : (161407,161520),
    "E7" : (161562,161948),
    "F1" : (162347,162577),
    "F2" : (162620,162882),
    "G1" : (165591,165632),
    "G2" : (165703,165732),
    "G3" : (165767,165815),
    "G4" : (165817,165818),
    "G5" : (165821,166143),
    "G6" : (166198,166383),
    "H1" : (166466,166850),
    "H2" : (166856,166964),
    "I1" : (167575,167680),
    "I2" : (167776,167844),
}

# Set default values for testing during local running
a_local_directory = "/pclmu7_home"
if os.path.exists(a_local_directory):
    #input = glob("/scratch/home_lucid/ebke/Data/data10_7TeV.00155112.*/*.root*")
    input = glob("/scratch/home_lucid/ebke/Data/mc09_7TeV.105924*/*.root*")
    options = {}
elif not "options" in dir():
    input = None
    raise RuntimeError("No options during non-local running!")

# setup athena
athena_setup(input, -1)

# do autoconfiguration of input
include ("RecExCommon/RecExCommon_topOptions.py")

# start of user Analysis definitions
gROOT.ProcessLine(".L VtxReweighting.C+")
gROOT.ProcessLine(".L MuonPtCorr.C+")


def or_func(c1, c2, delta):
    return lambda e : [x for x in getattr(e, c1) 
                       if min([100] + [x.hlv().deltaR(y.hlv()) 
                              for y in getattr(e, c2) 
                              if not x == y]) 
                       > delta]

def cached_property(f):
    return property(event_cache(f))

class MyMint(AnalysisAlgorithm):

    els = AnalysisAlgorithm.electrons
    mus = AnalysisAlgorithm.muons
    @cached_property
    def jets(self):
        return self.sg["AntiKt4H1TopoJets"]

    def __init__(self, name):
        super(MyMint, self).__init__(name)

    def initialize_trigger(self):

        # acquire trigger tool
        self.tool_tdt = PyAthena.py_tool('Trig::TrigDecisionTool/TrigDecisionTool')

        # initialize trigger maps
        trig_mc = (("L1_EM14", None, None), ("L1_MU10", None, None))
        trig_AD = (("L1_EM10", None, None), ("L1_mu6", None, None))
        trig_EF = ((None, None, "EF_e10_medium"), (None, None, "EF_mu10_MG"))
        trig_G4 = ((None, None, "EF_e15_medium"), (None, None, "EF_mu10_MG"))
        trig_GH = ((None, None, "EF_e15_medium"), (None, None, "EF_mu13_MG"))
        trig_I  = ((None, None, "EF_e15_medium"), (None, None, "EF_mu13_MG_tight"))

        # map periods to triggers        
        triggers = {"MC": trig_mc}
        for p in ("A", "B", "C", "D"):
            triggers[p] = trig_AD
        for p in [k for k in run_to_period.keys() if k[0] in ("E", "F")]:
            triggers[p] = trig_EF
        for p in ("G1", "G2", "G3", "G4"):
            triggers[p] = trig_G4
        for p in ("G5", "G6", "H1", "H2"):
            triggers[p] = trig_GH
        for p in ("I1", "I2"):
            triggers[p] = trig_I
        self.triggers = triggers

    def passed_trigger(self, channel, level):
        """pass trigger. channel in 'mumu', 'ee', 'emu', 
            level 0 is L1, 1 is L2 and 2 is EF
        """
        assert level in (0, 1, 2)
        assert channel in ("mumu", "ee", "emu")
        trig_em, trig_mu = self.triggers[self.period]
        trig_em, trig_mu = trig_em[level], trig_mu[level]
        passed = self.tool_tdt.isPassed
        if channel == "emu":
            if trig_em is None or trig_mu is None:
                return True
            return bool(passed(trig_em) or passed(trig_mu))
        elif channel == "mumu":
            return True if trig_mu is None else bool(passed(trig_mu))
        elif channel == "ee":
            return True if trig_em is None else bool(passed(trig_em))

    def initialize_stream_overlap(self):
        # read overlap files
        self.overlap_cache = {}
        pickles = [f for f in os.listdir(".") if f.startswith("overlap") and f.endswith(".pickle")]
        for pickle in pickles:
            self.overlap_cache.update(load(open(pickle)))
        print "--------- STREAM OVERLAP REMOVAL INFO ---------"
        print "read %i files:" % len(pickles)
        for pickle in pickles:
            print " * %s" % pickle
        print "list of runs:"
        print " ".join("%i" % run for run in sorted(self.overlap_cache.keys()))
        print "overlap per run:"
        for run in sorted(self.overlap_cache.keys()):
            print "%s : %i" % (run, len(self.overlap_cache[run]))
        print "--------- END STREAM OVERLAP REMOVAL INFO ---------"

    def initialize_period(self):
        # set period cache
        self._period = "I1"
        self._period_first, self._period_last = run_to_period[self._period]

    @cached_property
    def period(self):
        run = self.run_number
        if self._period_first <= run <= self._period_last:
            return self._period
        for period, (first, last) in run_to_period.items():
            if first <= run <= last:
                self._period = period
                self._period_first = first
                self._period_last = last
                return self._period
        raise RuntimeError("Run outside known periods!") 

    @cached_property
    def passed_grl(event):
        return (event.run_number, event.lumi_block) in event.grl

    @cached_property
    def is_overlap(self):
        if self.is_mc:
            return False
        run, event = self.run_number, self.event_number
        if not int(run) in self.overlap_cache:
            return False
        elif int(event) in self.overlap_cache[run]:
            return True
        else:
            return False

    @cached_property
    def staco_combined(e):
        return [mu for mu in e.sg["StacoMuonCollection"] if any(mu.isAuthor(i) for i in (5,6,7))]

    @cached_property
    def muid_combined(e):
        return [mu for mu in e.sg["MuidMuonCollection"] if any(mu.isAuthor(i) for i in (11,12,13,18))]


    @cached_property
    def passed_d3pd(e):
        for mu in e.staco_combined + e.muid_combined:
            if mu.pt() > 10*GeV and abs(mu.eta()) <  2.7:
                return True
        for el in e.els:
            if el.cluster().et() > 10*GeV and abs(el.cluster().eta()) <  2.7:
                return True
        return False

    @cached_property
    def met(self):
        if self.muon_algo == "Staco":
            midmet = "MET_Muid"
        else:
            midmet = "MET_MuonBoy"
        self.metX = self.sg["MET_LocHadTopo"].etx() + self.sg[midmet].etx() - self.sg["MET_RefMuon_Track"].etx()
        self.metY = self.sg["MET_LocHadTopo"].ety() + self.sg[midmet].ety() - self.sg["MET_RefMuon_Track"].ety()
        return self.metX, self.metY
    
    @cached_property
    def met_et(self):
        x, y = self.met
        return (x**2 + y**2)**0.5

    @cached_property
    def met_phi(self):
        x, y = self.met
        return atan2(x, y)

    @cached_property
    def vertices(self):
        return self.sg["VxPrimaryCandidate"]

    @cached_property
    def good_vertices(self):
        return [vx for vx in self.vertices if len(vx.vxTrackAtVertex()) >= 3]

    def initialize_jets(self):
        import PyCintex
        PyCintex.loadDictionary("JetUtils")
        from ROOT import JetCaloHelper, JetCaloQualityUtils
        self.jet_emf = lambda jet : JetCaloHelper.jetEMFraction(jet)
        self.jet_hecF = lambda jet : JetCaloQualityUtils.hecF(jet)

    @event_cache
    def is_bad_jet(self, jet, tight=False):
        quality = jet.getMoment("LArQuality")
        emf = self.jet_emf(jet)
        hecf = self.jet_hecF(jet)
        n90 = jet.getMoment("n90")
        time = jet.getMoment("Timing")
        fmax = jet.getMoment("fmax") # See https://twiki.cern.ch/twiki/bin/view/AtlasProtected/BaslinecutsforWWCONF
        eta = jet.eta()

        #  bool isBad(BadJetCategory criteria, double quality, double n90, double emf, double hecf, double time,double fmax, double eta)
        if emf>0.95 and abs(quality)>0.8:
            return True
        if hecf > 0.8 and n90 <= 5:                          
            return True
        if hecf > 0.5 and abs(quality) > 0.5:              
            return True       
        if abs(time) > 25:                              
            return True
        if emf < 0.05:                                    
            return True
        if fmax > 0.99 and abs(eta)<2:
            return True
      
        if(tight):
            if emf < 0.1:                                  
                return True
            if hecf > (1-abs(quality)):
                return True 
            if emf > 0.9 and abs(quality) > 0.6:            
                return True
            if hecf > 0.3 and abs(quality) > 0.3:           
                return True
            if fmax > 0.95 and abs(eta) < 2:
                return True
        return False

    def is_met_veto_jet(self, jet):
        return self.is_bad_jet(jet) and jet.pt() > 20*GeV and abs(jet.eta()) < 3

    @cached_property
    def leptons(event):
        return list(reversed(sorted(event.selected_mus + event.selected_els)))

    @cached_property
    def ll(event):
        if len(event.leptons) >= 2:
            l1, l2 = event.leptons[:2]
            return l1.hlv() + l2.hlv()

    #@cached_property
    def get_perigee(self, l, id_only=False):
        tp = getIDTP(l) if id_only else getTP(l)
        if len(self.vertices) > 0:
            v0 = self.vertices[0].recVertex().position()
            return self.tool_ttv.perigeeAtVertex(tp, v0) 
        else:
            return self.tool_ttv.perigeeAtVertex(tp) 

    def get_d0(self, l):
        return self.get_perigee(l, False).parameters()[0]

    def get_d0_id(self, l):
        return self.get_perigee(l, True).parameters()[0]

    def get_z0(self, l):
        return self.get_perigee(l, False).parameters()[1]
    
    def get_z0_id(self, l):
        return self.get_perigee(l, True).parameters()[1]

    @cached_property
    def l1(self):
        return self.leptons[0]

    @cached_property
    def l2(self):
        return self.leptons[1]

    def init(self):
        self.initialize_period()
        self.initialize_trigger()
        self.initialize_stream_overlap()
        self.initialize_jets()

        self.tool_ttv = PyAthena.py_tool("Reco::TrackToVertex", iface="Reco::ITrackToVertex")

        ww = CutGroup("ww", self.h)

        #independent cuts
        ww(Cut("D3PD", lambda e : e.passed_d3pd))
        ww(Cut("GRL", lambda e : e.passed_grl))
        ww(Cut("overlap", lambda e : not e.is_overlap))
        for c in ("mumu", "ee", "emu"):
            ww(Cut("L1_%s"%c, lambda e, c=c : e.passed_trigger(c, 0)))
            ww(Cut("L2_%s"%c, lambda e, c=c : e.passed_trigger(c, 1)))
            ww(Cut("EF_%s"%c, lambda e, c=c : e.passed_trigger(c, 2)))
        ww(Cut("MET", lambda e : e.met_et, lambda x : x > 30*GeV))
        ww(Cut("PV0", lambda e : len(e.vertices) > 0))
        ww(Cut("PVG", lambda e : len(e.good_vertices) > 0))
        #acs("vx_z", "vx", lambda vx : vx.recVertex().position().z(), lambda z : abs(z) < 150*mm, lambda e : len(e.vx), lambda n : n > 0)

        self.muon_cuts(ww.make_subgroup("muons", "mus"))
        self.electron_cuts(ww.make_subgroup("electrons", "els"))
        self.jet_cuts(ww.make_subgroup("jets", "jets"))

        self.ww = ww
    
        ww(SetContainer("selected_mus", lambda e : ww.selected(e, "ww/muons")))
        ww(SetContainer("preOR_els", lambda e : ww.selected(e, "ww/electrons")))
        ww(SetContainer("preOR_jets", lambda e : ww.selected(e, "ww/jets")))
        ww(SetContainer("preOR_bad_jets", lambda e : [j for j in e.jets if e.is_met_veto_jet(j)]))

        ww(SetContainer("midOR_els", or_func("preOR_els", "selected_mus", 0.1)))
        ww(SetContainer("selected_els", or_func("preOR_els", "preOR_els", 0.1)))
        ww(SetContainer("selected_jets", or_func("preOR_jets", "selected_els", 0.3)))
        ww(SetContainer("bad_jets", or_func("preOR_bad_jets", "selected_els", 0.3)))

        ww(Cut("two_leptons", lambda e : len(e.leptons) == 2))
        ww(Cut("ee", lambda e : len(e.selected_els) == 2 and len(e.selected_mus) == 0))
        ww(Cut("em", lambda e : len(e.selected_els) == 1 and len(e.selected_mus) == 1))
        ww(Cut("mm", lambda e : len(e.selected_els) == 0 and len(e.selected_mus) == 2))

        ww(Cut("met_cleaning", lambda e : len(e.bad_jets) == 0))

        ll = lambda e : len(e.leptons) >= 2

        ww(Cut("OS", lambda e : e.l1.charge() + e.l2.charge() == 0, dep=ll))

        #ww(Cut("C2_dRll", lambda e : e.leps[0].hlv().deltaR(e.leps[1].hlv()), lambda x : x > 0.1)
        #ww(Cut("C3_dRlj", lambda e : min([100] + [e.leps[0].hlv().deltaR(jet.hlv()) for jet in e.jets] + [e.leps[1].hlv().deltaR(jet.hlv()) for jet in e.jets]), lambda x : x > 0.3)
        #ww(Cut("C4_llpT", lambda e : e.ll.perp(), lambda x : x > 30*GeV
        #ww(Cut("D_z0", lambda e : abs(e.get_z0(e.l1) - e.get_z0(e.l2)) < 0.8, dep=ll))
        ww(Cut("D_z0_id", lambda e : abs(e.get_z0_id(e.l1) - e.get_z0_id(e.l2)) < 0.8, dep=ll))
        ww(Cut("llm_gt15", lambda e : e.ll.m() > 15*GeV, dep=ll))
        ww(Cut("llm_mZ10", lambda e : abs(e.ll.m() - MZ) > 10*GeV, dep=ll))
        ww(Cut("llpT_gt30", lambda e : e.ll.perp() > 30*GeV, dep=ll))

        ww(Cut("0jets", lambda e : len(e.selected_jets) == 0))

        # histograms
        ww(Histo(name="ll_m", b=[(100,0,100)], 
                         value = lambda e : (e.ll.m()/GeV,), 
                         req = ("two_leptons",),
                         cross = ("mm",)
                         ))

        ww(Histo(name="n_jets", b=[(20,0,20)], 
                         value = lambda e : len(e.selected_jets),
                         cross = ("met_cleaning",)
                         ))

        ww.initialize()
        self.tasks.append(lambda e : ww.execute(e))
        return 

    def muon_cuts(self, cg):
        import PyCintex
        PyCintex.loadDictionary("muonEventDict")
        from ROOT import MuonParameters
        if self.muon_algo == "Muid":
            good_author = lambda mu : mu.isAuthor(MuonParameters.MuidCo)
        else:
            good_author = lambda mu : mu.isAuthor(MuonParameters.STACO) and mu.isCombinedMuon() == 1

        cg(Cut("author", good_author))
        cg(Cut("pt", lambda mu : mu.pt() > 20*GeV, 
                            dep=good_author))
        cg(Cut("msidmatch", lambda mu : abs(mu.inDetTrackParticle().pt() - mu.muonExtrapolatedTrackParticle().pt()) < 15*GeV, 
                            dep=good_author))
        cg(Cut("mspt", lambda mu : mu.muonExtrapolatedTrackParticle().pt() > 10*GeV, 
                            dep=good_author))
        cg(Cut("eta", lambda mu : abs(mu.eta()) < 2.4))
        def vx_id_err(mu):
            vxp = self.vertices[0].recVertex().position()
            pavV0 = self.tool_ttv.perigeeAtVertex(mu.inDetTrackParticle(), vxp)
            return pavV0.parameters()[0]/pavV0.localErrorMatrix().error(0)
        cg(Cut("vx", lambda mu : abs(vx_id_err(mu)) < 10, 
                            dep=lambda mu : good_author(mu) and len(self.vertices) > 0))
        cg(Cut("ptcone20", lambda mu : mu.parameter(MuonParameters.ptcone20)/mu.pt() < 0.1))
        return cg

    def electron_cuts(self, cg):
    # container selection electrons - all standalone
        # Electron Filters:
        import PyCintex
        PyCintex.loadDictionary('egammaEnumsDict')
        gROOT.ProcessLine(".L checkOQ.C+")
        from ROOT import egammaParameters, egammaOQ
        egOQ = egammaOQ()
        egOQ.initialize()
        from robustIsEMDefs import elRobusterTight

        cg(Cut("author", lambda el : el.author() in (1,3)))

        def author(el):
            return el.author() in (1,3)

        def pass_otx(el):
            rn = 999999 if self.is_mc else self.run_number
            eta, phi = el.cluster().eta(), el.cluster().phi()
            return egOQ.checkOQClusterElectron(rn, eta, phi) != 3
        cg(Cut("otx", pass_otx, dep=author))

        def cluster_pt(el):
            return el.cluster().e()*sin(theta_from_eta(el.cluster().eta()))
        cg(Cut("pt", lambda el : cluster_pt(el) > 20*GeV, dep=author))


        def eta_in_range(eta):
            return abs(eta) < 2.47 and not (1.37 <= abs(eta) <= 1.52)
        cg(Cut("eta", lambda el: eta_in_range(el.cluster().eta()), dep=author))

        cg(Cut("robusterTight", lambda el : elRobusterTight(el), dep=author))

        def vertex0_d0_sig(el):
            assert self.vertices
            assert self.vertices[0]
            assert self.vertices[0].recVertex()
            assert self.vertices[0].recVertex().position()
            assert el.trackParticle()    
            vxp = self.vertices[0].recVertex().position()
            pavV0 = self.tool_ttv.perigeeAtVertex(el.trackParticle(), vxp)
            return pavV0.parameters()[0]/pavV0.localErrorMatrix().error(0)

        cg(Cut("vertex_d0", lambda el : abs(vertex0_d0_sig(el)) < 10, 
                            dep=lambda el : author(el) and self.vertices))

        cg(Cut("etiso30", lambda el : el.detailValue(egammaParameters.etcone30) < 6*GeV))
        return cg

    def jet_cuts(self, cg):
    # container selection jets - all standalone
        # Jet Filters
        cg(Cut("bad", lambda jet : not self.is_bad_jet(jet)))
        cg(Cut("pt", lambda jet : jet.pt() > 20*GeV))
        cg(Cut("eta", lambda jet : abs(jet.eta()) < 3))


myalg = None
accept_algs = []
for mu_algo in ["Staco", "Muid"]:
    name = "MINTY_%s" % (mu_algo)
    myalg = MyMint(name)
    myalg.muon_algo = mu_algo
    #myalg.tasks.append(lambda e : e.h.get("ll_m", b=[(100,0,100)])(e.ll.m()/GeV) if e.ll else None)
    #myalg.tasks.append(lambda e : e.h.get("ll_pt",b=[(100,0,100)])(e.ll.perp()/GeV) if e.ll else None)
    topSequence += myalg
    accept_algs.append(name)

if "skim" in options:
    setup_pool_skim("MintySkim.AOD.root", accept_algs)

