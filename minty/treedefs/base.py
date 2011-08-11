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
from egammaAnalysisUtils import CaloIsoCorrection, GetPtEDCorrectedIsolation, GetPtNPVCorrectedIsolation

import ROOT as R

from ..utils import event_cache

from .conditional import HasConditionals, data10, data11, rel15, rel16

AmbiguityResolution_Photon_Mask = 1 << 23
TrackBlayer_Electron_Mask = 1 << 16

# https://twiki.cern.ch/twiki/bin/view/AtlasProtected/LArCleaningAndObjectQuality#Details_object_quality_flag_and
# Grepability
# 0x8000000 == 134217728 == 0b1000 0000 0000 0000 0000 0000 0000
LARBITS_OUTOFTIME_CLUSTER = 1 << 26
LARBITS_PHOTON_CLEANING = 1 << 27

# 0x00085a6 == 34214 == 0b1000 0101 1010 0110
OQ_BAD_BITS = 0x00085a6

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
        """
        rootname: the thing that appears before the variable, e.g. "ph"
        leafname: the name of the variable
        """
        tuptype = CurrentVS.args.tuple_type
        
        # Three possible overrides: 
        if tuptype in kwargs:
            # Name specified for the tuple type
            varname = kwargs[tuptype]
        elif args:
            # Name specified for all other tuple types that aren't in kwargs
            (varname,) = args
        else:
            # Name not specifed, use the one we assigned to
            varname = leafname
        	
        if callable(varname):
            res = varname(rootname, leafname)
        elif "{" in varname:
            res = varname.replace("{rootname}", rootname)
            # Can't use format because of potential KeyErrors.
            #format(rootname=rootname, leafname="{leafname}")
        elif rootname:
            if "{leafname}" in rootname:
                res = rootname.replace("{leafname}", varname)
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
    g20_loose = g40_loose = TI.bool
    _2e15_loose = TI.bool(naming("2e15_loose"))
    e10_loose = e20_loose = TI.bool
    e20_medium = TI.bool
    #"""

class Vertex(object):
    __rootname__ = staticmethod(naming(eg="vxp", smwz="vxp", pau="PV", ph="PV"))
    
    nTracks = TI.int(naming(pau="ntracks"))
    z = TI.int(naming(pau="ID_zvertex"))
    
class Jet(Fourvec_PtEtaPhiE):
    #__rootname__ = "jet"
    __rootname__ = staticmethod(naming(eg="jet_akt4topoem", 
                                       smwz="jet", 
                                       ph="jet_AntiKt4TopoEMJets"))
    #isBad = TI.bool
    #isGood = TI.bool
    #isUgly = TI.bool
    
    emFraction = TI.float(naming(eg="emfrac", 
                                 ph="emfrac"))
    quality = TI.float(naming(eg="LArQuality",
                              ph="LArQuality"))
    
class EGamma(Particle, HasConditionals):
    isEM = TI.float
    etas1 = TI.float(naming(pau="etaS1"))
    etas2 = TI.float(naming(pau="etaS2"))
    etap  = TI.float
    
    author = TI.int
    
    oq_function = None # Populated by child classes
    OQ = TI.int(selfcn=data11) # (data11)
    goodOQ = TI.int(selfcn=data11)
    OQRecalc = TI.int(selfcn=data11)
    
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
        return not self.OQ & OQ_BAD_BITS
    
    @data10
    @property
    def pass_jetcleaning(self):
        return self.good_jet_quality
        
    @data11
    @property
    def pass_jetcleaning(self):
        return not self.OQ & LARBITS_PHOTON_CLEANING
    
    @property
    def pass_timing(self):
        return not self.OQ & LARBITS_OUTOFTIME_CLUSTER
    
    @property
    def pass_photoncleaning(self):
        return not (not self.pass_jetcleaning and 
                    (self.reta > 0.98 or self.rphi > 1 or self.pass_timing))
        #  !( (ph_OQ&134217728)!=0 && (ph_reta>0.98||ph_rphi>1.0||(ph_OQ&67108864)!=0) )
        
        #! (badjet && (out or out or outoftime))
        #goodjet or not x
        #x = (not out and not out and not outoftime)
        #x happens when eta and phi are both small, and the out of time bit is not set.
        #not x happens if it's out, or if it's out of time.
    
    @property
    def pass_fiducial_eta(self):
        return abs(self.etas2) < 1.37 or 1.52 < abs(self.etas2) < 2.37
    
    @property
    def et(self):
        try:
            return self.cl.E / cosh(self.etas2)
        except (ZeroDivisionError, OverflowError):
            return -99999
    
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
        except (ZeroDivisionError, OverflowError):
            return -99999
        
    @property
    def Rhad1(self):
        try:
            return self.Ethad1 / (self.cl.E / cosh(self.etas2))
        except (ZeroDivisionError, OverflowError):
            return -99999
    
    @property
    def Eratio(self):
        try:
            return (self.emaxs1 - self.Emax2) / (self.emaxs1 + self.Emax2)
        except (ZeroDivisionError, OverflowError):
            return -99999
    
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
    
    deltaEs = TI.float
    deltaEmax2 = TI.float
    depth   = TI.float
    Ethad   = TI.float(naming(pau="shwr_EtHad"))
    Ethad1  = TI.float(naming(pau="shwr_EtHad1"))
    E277    = TI.float(naming(pau="shwr_E277"))
    E237    = TI.float(naming(pau="shwr_E237"))
    E233    = TI.float(naming(pau="shwr_E233"))
    
    Emins1  = TI.float(naming(pau="shwr_Emin")) 
    emaxs1  = TI.float(naming(pau="shwr_Emax1"))
    Emax2   = TI.float(naming(pau="shwr_Emax2"))
    f1      = TI.float(naming(pau="shwr_f1"))
    f1core  = TI.float
    f3      = TI.float(naming(pau="shwr_f3"))
    f3core  = TI.float
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
    
    Etcone20_ED_corrected = TI.float
    Etcone30_ED_corrected = TI.float
    Etcone40_ED_corrected = TI.float
    
    class Cluster(Particle):
        """
        egamma: ph_cl_*
        pau:    ph_*_clus
        """
    cl = TI.instance(Cluster, naming(pau="{rootname}_{leafname}_clus"))
    time = TI.float
        
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
    
    class Conv(object):
        R = TI.float(naming(lambda a, b: "{0}_Rconv".format(Photon.__rootname__)))
        
        __naming__ = staticmethod(naming(ph="{rootname}_{leafname}"))
        
    conv = TI.instance(Conv, Conv.__naming__)
    
    @property
    def _part_type(self):
        return "CONVERTED_PHOTON" if self.isConv else "UNCONVERTED_PHOTON"
    
    loose = TI.float(naming(pau="isPhotonLoose"))
    tight = TI.float(naming(pau="isPhotonTight"))
    
    imatchRecJet = TI.float(naming(ph="jet_AntiKt4TopoEMJets_matched", 
                                   eg="jet_akt4topoem_matched"))
    
    #L1_e = TI.float(naming(pau="L1_e"))
    
    isConv  = TI.bool
    
    oq_function = check_photon
    
    @property
    def pt_via_clE_etas2(self):
        return self.cl.E / cosh(self.etas2)
    
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
    
    def Etcone40_PtED_corrected(self, is_mc=False):
        return GetPtEDCorrectedIsolation(
            self.Etcone40, 
            self.Etcone40_ED_corrected, 
            self.cl.E, 
            self.etas2, 
            self.etap, 
            self.cl.eta, 
            40,
            is_mc,
            self.Etcone40,
            self.isConv,
            CaloIsoCorrection.PHOTON)
    
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
    def nontight(self):
        return not self.isEM & 0x45fc01
    
    @property
    @event_cache
    def robust_tight(self):
        return self.robust_idtool.PhotonCutsTight(3)
        
    @property
    def ambiguity_resolved(self):
        return not (self.isEM & AmbiguityResolution_Photon_Mask)
    
    @property
    @event_cache
    def robust_isEM(self):
        return self.robust_idtool.isEM(3)
    
    @property
    def jet(self):
        "Only used for 2010 PAU."
        jetidx = self.imatchRecJet
        if jetidx < 0:
            return None
        return self._event.jets[jetidx]
        
    @property
    def good_jet_quality(self):
        "Only used for 2010 PAU."
        j = self.jet
        return j is None or j.emFraction < 0.95 or j.quality < 0.8
    
    @rel15
    @property
    def E_corrected(self):
        abs_eta = abs(self.etas2)
        if 0 <= abs_eta < 1.4:
            return self.E / (1. - 0.0096)
        else: #if 1.4 <= abs_eta < 2.5:
            return self.E / (1. + 0.0189)
        #else:
            #raise NotImplementedError
            
    @rel16
    @property
    def E_corrected(self, n=0):
        # For electrons:
        #et = cl_e/cosh(trk_eta) if (nSCT + nPix) >= 4) otherwise  et = cl_et 
        
        cl = self.cl
        E, phi = cl.E, cl.phi
        etas2 = self.etas2
        cl_et = cl.E / cosh(etas2)
        return v16_E_correction(etas2, phi, E, cl_et, n, self._part_type)

    def compute_corrected(self, vertex_z):
        self.corrected = self.corrected_fourvec(vertex_z)

    @event_cache
    def corrected_fourvec(self, vertex_z):
        
        eta_corrected = self.eta_corrected(vertex_z)
        
        E_corrected = self.E_corrected
        pt_corrected = E_corrected / cosh(eta_corrected)
        
        v = Fourvec_PtEtaPhiE(pt_corrected, eta_corrected, self.phi, E_corrected)
        v.isConv = self.isConv
        return v
    
    def eta_corrected(self, vertex_z):
        if abs(self.etas1) < 1.5:
            R = self.RZ_1stSampling_cscopt2
            Z = R * sinh(self.etas1)
            
        else:
            Z = self.RZ_1stSampling_cscopt2
            R = Z / sinh(self.etas1)
                
        return asinh((Z - vertex_z) / R)
        
    @property
    def RZ_1stSampling_cscopt2(self):
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
    
    
    class Truth(EGamma.Truth):
        pass
    truth = TI.instance(Truth, Truth.naming, VariableSelection.have_truth)
    
    def EtCone20_ptNPV_corrected(self, npv_withtracks, is_mc=False):
        return GetPtNPVCorrectedIsolation(
            npv_withtracks,
            self.cl.E,
            self.etas2,
            self.etap,
            self.cl.eta,
            20,
            is_mc,
            self.Etcone20,
            False, # Conversion, ignored for electrons
            # Default parttype is electron
            )
    
    @property
    def hit_dependent_pt(self):
        if self.nSCTHits + self.nPixHits >= 4:
            # If we have more than four hits, it's better to use track direction.
            return self.cl.E / cosh(self.track.eta)
        return self.cl.pt
    
    @property
    def has_blayer(self):
        return not self.isEM & TrackBlayer_Electron_Mask
    
    @property
    def pass_blayer_check(self):
        """
        "Require All Electrons have BLayer if Expected"
        """
        return self.has_blayer if self.expectHitInBLayer else True
    
    @property
    def good_jet_quality(self):
        "Only used for 2010 PAU. No jet quality for electrons."
        return True
    
    @property
    def pass_fiducial(self):
        return (self.et > 20000 and 
                (abs(self.etas2) < 1.37 or 1.52 <= abs(self.etas2) < 2.47))
    
    @data11
    @property
    def my_oq(self):
        # 0x5a6 == 1446 == 0b0101 1010 0110
        return not self.OQ & 0x05a6
        
    loose  = TI.bool(naming(pau="isElectronLoose"))
    medium = TI.bool(naming(pau="isElectronMedium"))
    tight  = TI.bool(naming(pau="isElectronTight"))
    
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
        
