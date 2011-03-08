from logging import getLogger; log = getLogger("minty.treedefs")

from math import tanh, cosh

from pytuple.readtuple import make_wrapper
from pytuple.treeinfo import treeinfo as TI
from pytuple.Fourvec import Fourvec_All, Fourvec_PtEtaPhiE

from PhotonIDTool import PhotonIDTool
from OQMaps import check_photon, check_electron

import ROOT as R

from ..utils import event_cache

from ..external.robustIsEMDefs import (
    isRobustLoose as isRobustLoose_electron,
    isRobustMedium as isRobustMedium_electron,
    isRobusterTight as isRobusterTight_electron)

@property
def raise_not_implemented(self):
    "When this property is accessed, an error is raised"
    raise NotImplementedError

class VariableSelection(object):
    have_truth = False
    tuple_type = "eg" # possibilities: "pau"
        
class CurrentVS:
    args = VariableSelection()

def naming(**kwargs):
    """
    Rewrite names according to kwargs.
    """
    def functor(rootname=None, leafname=None):
        tuptype = CurrentVS.args.tuple_type
        varname = kwargs.get(tuptype, leafname)
        if callable(varname):
            res = varname(rootname, leafname)
        elif "{" in varname:
            res = varname.replace("{rootname}", rootname) #format(rootname=rootname, leafname="{leafname}")
        elif rootname:
            if "{leafname}" in rootname:
                res = rootname.replace("{leafname}", leafname)
            else:
                res = "%s_%s" % (rootname, varname) if rootname else varname
        else:
            res = varname
        #print "Created new ROOT branch name: ", rootname, leafname, res
        return res
    return functor

def pairs(inputs):
    if len(inputs) < 2:
        return
    for i, o1 in enumerate(inputs):
        for o2 in inputs[i+1:]:
            yield o1, o2
            
def by_pt(objects):
    return sorted(objects, key=lambda o: o.pt)
            
class Global(object):
    RunNumber = TI.int(naming(pau="Run"))
    EventNumber = TI.int(naming(pau="Event"))
    LumiBlock = TI.int(naming(eg="lbn"))
    
    # Populated by AnalysisBase.setup_objects
    _grl = None
    _event = None
    
    @property
    def is_grl(self):
        return (self.RunNumber, self.LumiBlock) in self._grl
        
    @property
    @event_cache
    def diphotons(self):
        return list(pairs(by_pt(self._event.photons)))
    
    @property
    @event_cache
    def dielectrons(self):
        return list(pairs(by_pt(self._event.electrons)))

class Particle(Fourvec_PtEtaPhiE):
    "Defines an object with (pt, eta, phi, E) available)."
    
    @property
    def in_barrel(self):
        return abs(self.etas2) < 1.37
    
    @property
    def in_crack(self):
        return 1.37 <= abs(self.etas2) < 1.52
        
    @property
    def in_endcap(self):
        return 1.52 <= abs(self.etas2) < 2.37
    
    @property
    def region_character(self):
        if self.in_barrel: return "B"
        if self.in_crack: return "C"
        if self.in_endcap: return "E"
        return "X"
        raise RuntimeError("Bad Eta: %.4f" % self.etas2)

class Trigger(object):
    _2g15_loose = g10_loose = g20_loose = g30_loose = g40_loose = 0

class Vertex(object):
    __rootname__ = staticmethod(naming(eg="vxp", pau="PV"))
    
    nTracks = TI.int(naming(pau="ntracks"))
    zvertex = TI.int(naming(pau="ID_zvertex"))
    
class Jet(Fourvec_PtEtaPhiE):
    __rootname__ = "jet"
    
    #isBad = TI.bool
    #isGood = TI.bool
    #isUgly = TI.bool
    
    emFraction = TI.float(naming(pau="emFraction"))
    quality = TI.float(naming(pau="quality"))
    
class EGamma(Particle):
    isEM = TI.float
    etas2 = TI.float(naming(pau="etaS2"))
    
    author = TI.int
    
    oq_function = None # Populated by child classes
    _event = None # Populated by AnalysisBase.setup_objects
    
    @property
    @event_cache
    def good_oq(self):
        run = self._event.RunNumber
        if run < 152166:
            # Sigh..
            # Use most recent monte carlo map.
            # In the future, use a weight.
            run = 500000
        oq = self.oq_function(run, self.cl.eta, self.cl.phi)
        return oq < 3
    
    @property
    def graviton2011_fiducial(self):
        return (self.loose and 
                self.cl.pt > 25000 and 
                not self.in_crack and 
                self.good_oq)
    
    @property
    def et(self):
        try:
            return self.cl.E / cosh(self.etas2)
        except ZeroDivisionError:
            return 0.
    
    @property
    def reta(self):
        return self.E237 / self.E277 if self.E277 else 0
        
    @property
    def rphi(self):
        return self.E233 / self.E237 if self.E237 else 0
    
    @property
    def Rhad(self):
        try:
            return self.Ethad / (self.cl.E / cosh(self.etas2))
        except ZeroDivisionError:
            return 0.
        
    @property
    def Rhad1(self):
        try:
            return self.Ethad1 / (self.cl.E / cosh(self.etas2))
        except ZeroDivisionError:
            return 0.
    
    @property
    def Eratio(self):
        try:
            return (self.emaxs1 - self.Emax2) / (self.emaxs1 + self.Emax2)
        except ZeroDivisionError:
            return 0.
    
    @property
    def deltaE(self):
        return self.Emax2 - self.Emins1
        
    @property
    def nontight(self):
        return not (self.isEM & 0x45fc01)
        
    @property
    def isolated(self):
        return self.EtCone40_corrected < 3000
        
    @property
    def nonisolated(self):
        return self.EtCone40_corrected > 5000
    
    isConv  = TI.bool
    
    Ethad   = TI.float(naming(pau="shwr_EtHad"))
    Ethad1  = TI.float(naming(pau="shwr_EtHad1"))
    E277    = TI.float(naming(pau="shwr_E277"))
    E237    = TI.float(naming(pau="shwr_E237"))
    E233    = TI.float(naming(pau="shwr_E233"))
    
    Emins1  = TI.float(naming(pau="shwr_Emin")) 
    emaxs1  = TI.float(naming(pau="shwr_Emax1"))
    Emax2   = TI.float(naming(pau="shwr_Emax2"))
    f1      = TI.float(naming(pau="shwr_f1"))
    fside   = TI.float(naming(pau="shwr_fracm"))
    weta2   = TI.float(naming(pau="shwr_weta2"))
    ws3     = TI.float(naming(pau="shwr_w1"))
    wstot   = TI.float(naming(pau="shwr_wtot"))
    
    EtCone20 = TI.float(naming(pau="shwr_EtCone20"))
    EtCone30 = TI.float(naming(pau="shwr_EtCone30"))
    EtCone40 = TI.float(naming(pau="shwr_EtCone40"))
    
    EtCone20_corrected = TI.float(naming(pau="shwr_EtCone20_corrected"))
    EtCone30_corrected = TI.float(naming(pau="shwr_EtCone30_corrected"))
    EtCone40_corrected = TI.float(naming(pau="shwr_EtCone40_corrected"))
    
    class Cluster(Particle):
        """
        egamma: ph_cl_*
        pau:    ph_*_clus
        """
    cl = TI.instance(Cluster, naming(pau="{rootname}_{leafname}_clus"))
        
    class Truth(Particle):
        """
        egamma: ph_truth_* => namepat = "%s_truth_"
        pau:    truth_ph_* => namepat = "truth_%s_"
        """
        
        # matched in pau is called "ph_matchMC"
        matched = TI.bool(naming(pau=lambda x, y: x.replace("{leafname}_", "match")))
        
        isPhotonFromHardProc = TI.bool
        
        naming = staticmethod(naming(eg ="{rootname}_truth_{leafname}",
                                     pau="{rootname}_{leafname}_MC"))
    truth = TI.instance(Truth, Truth.naming, VariableSelection.have_truth)
                    
class Photon(EGamma):
    __rootname__ = "ph"
    particle = "photon"
    
    loose = TI.float(naming(pau="isPhotonLoose"))
    tight = TI.float(naming(pau="isPhotonTight"))
    imatchRecJet = TI.float(naming(pau="imatchRecJet"))
    
    
    L1_e = TI.float(naming(pau="L1_e"))
    
    EF_matchPass = TI.int
    
    oq_function = check_photon
    
    @property
    @event_cache
    def robust_idtool(self):
        return PhotonIDTool(
            self.et, self.etas2,
            self.Ethad1, self.Ethad,
            self.E277, self.E237, self.E233,
            self.weta2,
            self.f1,
            self.emaxs1, self.Emax2, self.Emins1,
            self.fside,
            self.wstot, self.ws3,
            self.isConv,        
        )
    
    @property
    @event_cache
    def robust_tight(self):
        return self.robust_idtool.PhotonCutsTight(3)
    
    @property
    @event_cache
    def robust_nontight(self):
        """
        """
        return not (self.robust_isEM & 0x45fc01)
    
    @property
    def robust_tight_test(self):
        return not (self.robust_isEM & 0xFFFFFFFF)
    
    @property
    @event_cache
    def robust_isEM(self):
        return self.robust_idtool.isEM(3)
        
    @property
    @event_cache
    def pass_fiducial(self):
        return (self.cl.pt >= 25000 and 
                (abs(self.etas2) < 1.37 or 1.52 <= abs(self.etas2) < 2.37))        

    @property
    def jet(self):
        jetidx = self.imatchRecJet
        if jetidx < 0:
            return None
        return self._event.jets[jetidx]
        
    @property
    def good_jet_quality(self):
        j = self.jet
        return j is None or j.emFraction < 0.95 or j.quality < 0.8
    
class Electron(EGamma):
    __rootname__ = "el"
    particle = "electron"
    
    oq_function = check_electron

    @property
    def robust_loose(self):
        args = self.isEM, abs(self.etas2), self.et, self.reta, self.weta2
        return isRobusterLoose_electron(*args)
        
    @property
    def robuster_tight(self):
        args = self.isEM, self.expectHitInBLayer, abs(self.etas2), self.et, self.reta, self.weta2
        return isRobusterTight_electron(*args)
    
    robust_nontight = 0 # Doesn't make sense for electrons (?)
    robust_tight = robuster_tight
    
    @property
    def pass_fiducial(self):
        return (self.et > 20000 and 
                (abs(self.etas2) < 1.37 or 1.52 <= abs(self.etas2) < 2.47))
                
    loose = TI.float(naming(pau="isElectronLoose"))
    tight = TI.float(naming(pau="isElectronTight"))
    expectHitInBLayer = TI.int
    
class TruthPhoton(Particle):
    __rootname__ = "truth_ph"
    
    iRecPhoton = TI.int
    isFromHardProc = TI.bool
    
    @property
    def pass_fiducial(self):
        return (self.pt >= 15000 and 
                (abs(self.eta) < 1.37 or 1.52 <= abs(self.eta) < 2.37))
                
    @property
    def reco(self):
        if self.iRecPhoton == -1:
            return None
        return self._event.photons[self.iRecPhoton]
        
