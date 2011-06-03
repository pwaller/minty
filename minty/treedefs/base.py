"""
Conventions:

Take this as an example:
    class Photon(...):
        __rootname__ = "ph"
        loose = TI.float(naming(pau="isPhotonLoose"))

This means that all photon objects have a ".loose", and their branch name on the
tuple is "{__rootname__}_loose". For tuples of type "pau", it's ph_isPhotonLoose.

"""


from logging import getLogger; log = getLogger("minty.treedefs")

from math import tanh, cosh, sinh, asinh

from pytuple.readtuple import make_wrapper
from pytuple.treeinfo import treeinfo as TI
from pytuple.Fourvec import Fourvec_All, Fourvec_PtEtaPhiE

from PhotonIDTool import PhotonIDTool
from OQMaps import check_photon, check_electron
from EnergyRescalerTool import v16_E_correction

import ROOT as R

from ..utils import event_cache

from ..external.robustIsEMDefs import (
    isRobustLoose as isRobustLoose_electron,
    isRobustMedium as isRobustMedium_electron,
    isRobusterTight as isRobusterTight_electron)

from .conditional import HasConditionals, data10, data11, rel15, rel16

AmbiguityResolution_Photon = 1 << 23

@property
def raise_not_implemented(self):
    "When this property is accessed, an error is raised"
    raise NotImplementedError

class VariableSelection(object):
    have_truth = False
    tuple_type = "eg" # possibilities: "pau", "ph"
        
class CurrentVS:
    args = VariableSelection()

def naming(*args, **kwargs):
    """
    Rewrite names according to kwargs.
    """
    def functor(rootname=None, leafname=None):
        tuptype = CurrentVS.args.tuple_type
        varname = kwargs.get(tuptype, leafname)
        if varname == leafname and args:
      		# If we just used leafname and args are specified, args[0] 
      		# over-rides.
        	varname = args[0]
        	
        if callable(varname):
            res = varname(rootname, leafname)
        elif "{" in varname:
            res = varname.replace("{rootname}", rootname) 
            # Can't use format because of potential KeyErrors.
            #format(rootname=rootname, leafname="{leafname}")
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
    LumiBlock = TI.int(naming("lbn", pau="LumiBlock"))
    
    larError = TI.int
    
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
	#"""
    _2g15_loose = TI.bool(naming("2g15_loose"))
    _2g20_loose = TI.bool(naming("2g20_loose"))
    g10_loose = g20_loose = g30_loose = g40_loose = TI.bool
    _2e15_loose = TI.bool(naming("2e15_loose"))
    e10_loose = e20_loose = e30_loose = TI.bool
    #"""

class Vertex(object):
    __rootname__ = staticmethod(naming(eg="vxp", smwz="vxp", pau="PV", ph="PV"))
    
    nTracks = TI.int(naming(pau="ntracks"))
    z = TI.int(naming(pau="ID_zvertex"))
    
class Jet(Fourvec_PtEtaPhiE):
    __rootname__ = "jet"
    
    #isBad = TI.bool
    #isGood = TI.bool
    #isUgly = TI.bool
    
    emFraction = TI.float(naming(eg="akt4topoem_emfrac", 
                                 ph="AntiKt4TopoEMJets_emfrac"))
    quality = TI.float(naming(eg="akt4topoem_LArQuality",
                              ph="AntiKt4TopoEMJets_LArQuality"))
    
class EGamma(Particle, HasConditionals):
    isEM = TI.float
    etas1 = TI.float(naming(pau="etaS1"))
    etas2 = TI.float(naming(pau="etaS2"))
    
    author = TI.int
    
    oq_function = None # Populated by child classes
    OQ = TI.int(selfcn=data11) # (data11)
    
    # Populated by AnalysisBase.setup_objects
    _part_type = None
    _event = None 
    _v16_energy_rescaler = None
    
    @data10
    @property
    @event_cache
    def my_oq(self):
        run = self._event.RunNumber
        if run < 152166:
            # Sigh..
            # Use most recent (PP! end of period I) monte carlo map.
            # In the future, use a weight.
            run = 166466
        oq = self.oq_function(run, self.cl.eta, self.cl.phi)
        return oq < 3
    
    @data11
    @property
    def my_oq(self):
        # 0x00085a6 == 34214 == 0b1000 0101 1010 0110
        return not self.OQ & 0x00085a6
    
    @data11
    @property
    def pass_jetcleaning(self):
        # 0x8000000 == 134217728 == 0b1000 0000 0000 0000 0000 0000 0000
        return not self.OQ & 0x8000000
    
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
        return self.Etcone40_corrected < 3000
        
    @property
    def nonisolated(self):
        return self.Etcone40_corrected > 5000
        
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
    
    Etcone20 = TI.float(naming(pau="shwr_EtCone20"))
    Etcone30 = TI.float(naming(pau="shwr_EtCone30"))
    Etcone40 = TI.float(naming(pau="shwr_EtCone40"))
    
    Etcone20_pt_corrected = TI.float(naming(pau="shwr_EtCone20_corrected"))
    Etcone30_pt_corrected = TI.float(naming(pau="shwr_EtCone30_corrected"))
    Etcone40_pt_corrected = TI.float(naming(pau="shwr_EtCone40_corrected"))
    
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
                
        naming = staticmethod(naming(eg ="{rootname}_truth_{leafname}",
                                     pau="{rootname}_{leafname}_MC"))
                    
class Photon(EGamma):
    __rootname__ = "ph"
    particle = "photon"
    
    class Truth(EGamma.Truth):
        isPhotonFromHardProc = TI.bool
    truth = TI.instance(Truth, Truth.naming, VariableSelection.have_truth)
    
    @property
    def _part_type(self):
        return "CONVERTED_PHOTON" if self.isConv else "UNCONVERTED_PHOTON"
    
    loose = TI.float(naming(pau="isPhotonLoose"))
    tight = TI.float(naming(pau="isPhotonTight"))
    
    imatchRecJet = TI.float(naming(ph="jet_AntiKt4TopoEMJets_matched", 
                                   eg="jet_akt4topoem_matched"))
    
    L1_e = TI.float(naming(pau="L1_e"))
    
    L1_matchPass = TI.int
    L2_matchPass = TI.int
    EF_matchPass = TI.int
    isConv  = TI.bool
    
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
    
    @rel15
    @property
    def my_loose(self):
        return self.robust_loose
        
    @rel16
    @property
    def my_loose(self):
        return self.loose and self.ambiguity_resolved
    
    @rel15
    @property
    def my_tight(self):
        return self.robust_tight
        
    @rel16
    @property
    def my_tight(self):
        return self.tight
    
    @property
    def robust_loose(self):
        return self.robust_idtool.PhotonCutsLoose2()
    
    @property
    @event_cache
    def robust_tight(self):
        return self.robust_idtool.PhotonCutsTight(3)
        
    @property
    def ambiguity_resolved(self):
        return not (self.isEM & AmbiguityResolution_Photon)
    
    @property
    @event_cache
    def robust_isEM(self):
        return self.robust_idtool.isEM(3)
        
    @property
    def pass_fiducial_eta(self):
        return abs(self.etas2) < 1.37 or 1.52 < abs(self.etas2) < 2.37
    
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
    
    def v16_E_corrected(self, n=0):
        # For electrons:
        #et = cl_e/cosh(trk_eta) if (nSCT + nPix) >= 4) otherwise  et = cl_et 
        
        cl = self.cl
        E, phi = cl.E, cl.phi
        etas2 = self.etas2
        cl_et = cl.E / cosh(etas2)
        aEC = self._v16_energy_rescaler.applyEnergyCorrection
        return aEC(etas2, phi, E, cl_et, n, self._part_type)
        
    def v16_corrections(self):
        E_corrected = self.v16_E_corrected()
        v = Fourvec_PtEtaPhiE(self.cl.pt, self.etas1, self.phi, E_corrected)
        v.isConv = self.isConv
        return v
    
    @property
    def v15_E_corrected(self):
        abs_eta = abs(self.etas2)
        if 0 <= abs_eta < 1.4:
            return self.E / (1. - 0.0096)
        else: #if 1.4 <= abs_eta < 2.5:
            return self.E / (1. + 0.0189)
        #else:
            #raise NotImplementedError

    def v15_corrections(self, vertex_z):
    
        if abs(self.etas1) < 1.5:
            R = self.v15_RZ_1stSampling_cscopt2
            Z = R * sinh(self.etas1)
            
        else:
            Z = self.v15_RZ_1stSampling_cscopt2
            R = Z / sinh(self.etas1)
        
        eta_corrected = asinh((Z - vertex_z) / R)
        
        E_corrected = self.v15_E_corrected
        pt_corrected = E_corrected / cosh(eta_corrected)
        
        v = Fourvec_PtEtaPhiE(pt_corrected, eta_corrected, self.phi, E_corrected)
        v.isConv = self.isConv
        return v
        
    @property
    def v15_RZ_1stSampling_cscopt2(self):
        # adapted from CaloDepthTool.cxx, double CaloDepthTool::cscopt2_parametrized(const CaloCell_ID::CaloSample sample,
        #  const double eta, const double /*phi*/ )
        # No warranty !!!

        radius = -99999

        aeta_1st_sampling = abs(self.etas1)

        if aeta_1st_sampling < 1.5:
            if aeta_1st_sampling < 0.8:
                radius = 1558.859292 - 4.990838*aeta_1st_sampling - 21.144279*aeta_1st_sampling*aeta_1st_sampling
            else:
                radius = 1522.775373 + 27.970192*aeta_1st_sampling - 21.104108*aeta_1st_sampling*aeta_1st_sampling
                
        else:
            if aeta_1st_sampling < 1.5:
                radius = 12453.297448 - 5735.787116*aeta_1st_sampling
            else:
                radius = 3790.671754
                
            if self.etas1 < 0.:
                radius = -radius
        
        return radius
        
class Electron(EGamma):
    __rootname__ = "el"
    particle = "electron"
    _part_type = "ELECTRON"
    
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
    def hit_dependent_pt(self):
        if self.nSCTHits + self.nPixHits >= 4:
            # If we have more than four hits, it's better to use track direction.
            return self.cl.E / cosh(self.track.eta)
        return self.cl.pt
    
    @property
    def pass_fiducial(self):
        return (self.et > 20000 and 
                (abs(self.etas2) < 1.37 or 1.52 <= abs(self.etas2) < 2.47))
                
    loose = TI.float(naming(pau="isElectronLoose"))
    tight = TI.float(naming(pau="isElectronTight"))
    
    expectHitInBLayer = TI.int
    nPixHits = nSCTHits = TI.int
    
    class Track(Particle):
        E = None # Tracks don't have energy.
    track = TI.instance(Track, naming(pau="{rootname}_{leafname}",
                                      ph="{rootname}_track{leafname}",
                                      eg="{rootname}_track{leafname}"))
    
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
        
