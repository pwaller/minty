from pytuple.readtuple import make_wrapper
from pytuple.treeinfo import treeinfo as TI
from pytuple.Fourvec import Fourvec_All, Fourvec_PtEtaPhiE
from math import tanh, cosh

from PhotonIDTool import get_photon_robust_tight
from OQMaps import check_photon, check_electron

import ROOT as R

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
            res = varname.format(rootname=rootname, leafname="{leafname}")
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

class Global(object):
    RunNumber = TI.int(naming(pau="Run"))
    EventNumber = TI.int(naming(pau="Event"))
    LumiBlock = TI.int(naming(eg="lbn"))
    
    _grl = None # Populated by AnalysisBase.setup_objects
    
    @property
    def is_grl(self):
        return (self.RunNumber, self.LumiBlock) in self._grl

class Particle(Fourvec_PtEtaPhiE):
    "Defines an object with (pt, eta, phi, E) available)."

class Trigger(object):
    g10_loose = TI.bool

class Vertex(object):
    __rootname__ = staticmethod(naming(eg="vxp", pau="PV"))
    
    nTracks = TI.int(naming(pau="ntracks"))
    
class Jet(Fourvec_PtEtaPhiE):
    pass
    
class EGamma(Particle):
    isEM = TI.float
    etas2 = TI.float(naming(pau="etaS2"))
    
    oq_function = None # Populated by child classes
    _event = None # Populated by AnalysisBase.setup_objects
    
    @property
    def good_oq(self):
        oq = self.oq_function(self._event.RunNumber, self.cl.eta, self.cl.phi)
        return oq < 3
    
    @property
    def reta(self):
        return self.E237 / self.E277 if self.E277 else 0
        
    @property
    def rphi(self):
        return self.E233 / self.E237 if self.E237 else 0
    
    @property
    def Rhad(self):
        return self.EtHad / (self.cl.E / cosh(self.etas2))
        
    @property
    def Rhad1(self):
        return self.EtHad1 / (self.cl.E / cosh(self.etas2))
    
    @property
    def Eratio(self):
        return (self.emaxs1 - self.Emax2) / (self.emaxs1 + self.Emax2)
    
    @property
    def deltaE(self):
        return self.Emax2 - self.Emins1
        
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
    truth = TI.instance(Truth, Truth.naming, VariableSelection.have_truth)
                    
class Photon(EGamma):
    __rootname__ = "ph"
    
    loose = TI.float(naming(pau="isPhotonLoose"))
    tight = TI.float(naming(pau="isPhotonTight"))
    
    oq_function = check_photon
    
    @property
    def robust_tight(self):
        return get_photon_robust_tight(self)
        
    @property
    def pass_fiducial(self):
        return (self.cl.pt >= 15000 and 
                (abs(self.etas2) < 1.37 or 1.52 <= abs(self.etas2) < 2.37))        

class Electron(EGamma):
    __rootname__ = "el"

    oq_function = check_electron

    # Not yet implemented
    pass_fiducial = robust_tight = 0

    loose = TI.float(naming(pau="isElectronLoose"))
    tight = TI.float(naming(pau="isElectronTight"))
