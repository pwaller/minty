#   John Alison <johnda@sas.upenn.edu>
   
#   Redefine the isEM definitions such that the Reta and w2 cuts are loosened at high eta.
   
#   Note: 
#   Currently the MC mismodels the Reta and w2 distributions at high large eta (|eta| > 1.8).
#   In addition the isEM cuts are relatively aggressive in this region, leading to data/MC 
#   disagrement in electron efficiency

import PyCintex
PyCintex.loadDictionary('egammaEnumsDict')

from ROOT import egammaParameters

from math import cosh

ClusterEtaRange_Electron = 0
ConversionMatch_Electron        =  1
ClusterHadronicLeakage_Electron = 2
ClusterMiddleEnergy_Electron = 3

ClusterEtaRange = 0
ClusterHadronicLeakage = 1
ClusterMiddleEnergy = 4
ClusterMiddleEratio37 = 5
ClusterMiddleEratio33 = 6
ClusterMiddleWidth = 7

ClusterStripsEratio_Electron    =  8
ClusterStripsDeltaEmax2_Electron =  9
ClusterStripsDeltaE_Electron    = 10
ClusterStripsWtot_Electron      = 11
ClusterStripsFracm_Electron     = 12
ClusterStripsWeta1c_Electron    = 13

ClusterStripsDEmaxs1_Electron   = 15
TrackBlayer_Electron            = 16
TrackPixel_Electron             = 17
TrackSi_Electron                = 18
TrackA0_Electron                = 19
TrackMatchEta_Electron          = 20
TrackMatchPhi_Electron          = 21
TrackMatchEoverP_Electron       = 22
TrackTRThits_Electron           = 24
TrackTRTratio_Electron          = 25
TrackTRTratio90_Electron        = 26
TrackA0Tight_Electron           = 27


HADLEAKETA_ELECTRON = (0x1 << ClusterEtaRange_Electron) | (0x1 << ClusterHadronicLeakage_Electron)
CALOSTRIPS_ELECTRON = (
    0x1 << ClusterStripsEratio_Electron     |
    0x1 << ClusterStripsDeltaEmax2_Electron |
    0x1 << ClusterStripsDeltaE_Electron     |
    0x1 << ClusterStripsWtot_Electron       |
    0x1 << ClusterStripsFracm_Electron      |
    0x1 << ClusterStripsWeta1c_Electron     |
    0x1 << ClusterStripsDEmaxs1_Electron    
    )

TRACKINGNOBLAYER_ELECTRON = (
    0x1 << TrackPixel_Electron   |
    0x1 << TrackSi_Electron      |
    0x1 << TrackA0_Electron)

TRACKMATCHDETA_ELECTRON = 0x1 << TrackMatchEta_Electron;

TRACKING_ELECTRON = TRACKINGNOBLAYER_ELECTRON | 0x1 << TrackBlayer_Electron

TRT_ELECTRON =  0x1 << TrackTRThits_Electron | 0x1 << TrackTRTratio_Electron

## Alison's definitions:
#loose
CALOMIDDLE_ELECTRON_NoReta_NoW2 = 0x1 << ClusterMiddleEnergy_Electron;
ElectronLoose_NoReta_NoW2 = CALOMIDDLE_ELECTRON_NoReta_NoW2 | HADLEAKETA_ELECTRON
#medium
CALO_ELECTRON_NoReta_NoW2 = ( 
    HADLEAKETA_ELECTRON | 
    CALOSTRIPS_ELECTRON | 
    CALOMIDDLE_ELECTRON_NoReta_NoW2 )

ElectronMedium_NOReta_NoW2 = (
    CALO_ELECTRON_NoReta_NoW2 | 
    TRACKINGNOBLAYER_ELECTRON | 
    TRACKMATCHDETA_ELECTRON  )

#tight
ElectronTightRobust_NoReta_NoW2 = (
    CALO_ELECTRON_NoReta_NoW2 | 
    TRACKING_ELECTRON | 
    0x1 << TrackMatchEta_Electron | 
    0x1 << TrackMatchEoverP_Electron | 
    0x1 << TrackA0Tight_Electron |
    0x1 << ConversionMatch_Electron |
    TRT_ELECTRON )
    
# Tight without the conversion requirement 
ElectronTightRobust_NoReta_NoW2_NoConvCut = ( 
    CALO_ELECTRON_NoReta_NoW2 | 
    TRACKING_ELECTRON | 
    0x1 << TrackMatchEta_Electron | 
    0x1 << TrackMatchEoverP_Electron | 
    0x1 << TrackA0Tight_Electron |
    TRT_ELECTRON )


print CALOMIDDLE_ELECTRON_NoReta_NoW2 
print ElectronLoose_NoReta_NoW2 
print CALOMIDDLE_ELECTRON_NoReta_NoW2 
print CALO_ELECTRON_NoReta_NoW2 
print ElectronMedium_NOReta_NoW2 
print ElectronTightRobust_NoReta_NoW2 
print ElectronTightRobust_NoReta_NoW2_NoConvCut 
print

def getVars(el):
    """
     The isRobustLoose, isRobustMedium, isRobusterTight methods take:
        - the electron isEM bit-mask
    - a bool indicating if we expect a BLayer hit. (isRobusterTight Only)
    - the electron cluster eta in the second sampling
         // eta position in second sampling
         float eta2   = fabs(cluster->etaBE(2)); //where cluster is the CaloCluster
    - the electron eT (IN MEV)
         // transverse energy in calorimeter (using eta position in second sampling)
         float et = cluster->energy()/cosh(eta2); //where cluster is the CaloCluster
    - the electron Reta
         // E(3*7) in 2nd sampling
         float e237   = shower->e237();
         // E(7*7) in 2nd sampling
         float e277   = shower->e277();
         float Reta = e237/e277;          //where shower is the EMShower
    - the electron w2
         // shower width in 2nd sampling
         float weta2c = shower->weta2();  //where shower is the EMShower 
    """
    isEM = el.isem()
    expectBLayer = el.detailValue(egammaParameters.expectHitInBLayer)
    eta = abs(el.cluster().etaBE(2))
    eT = el.cluster().energy()/cosh(eta)
    if el.detailValue(egammaParameters.e277):
        Reta = el.detailValue(egammaParameters.e237) / el.detailValue(egammaParameters.e277)
    else:
        Reta = 0
    w2 = el.detailValue(egammaParameters.weta2)
    return isEM, expectBLayer, eta, eT, Reta, w2

def elRobustLoose(el):
    isEM, expectBLayer, eta, eT, Reta, w2 = getVars(el)
    return isRobustLoose(isEM, eta, eT, Reta, w2)
    
def elRobustMedium(el):
    isEM, expectBLayer, eta, eT, Reta, w2 = getVars(el)
    return isRobustMedium(isEM, eta, eT, Reta, w2)

def elRobusterTight(el):
    isEM, expectBLayer, eta, eT, Reta, w2 = getVars(el)
    return isRobusterTight(isEM, expectBLayer, eta, eT, Reta, w2)


def isRobustLoose(isEM, eta, eT, Reta, w2):

    absEta = abs(eta)

    ## Does it pass the loose isEM with Reta and w2 removed?
    if (isEM & ElectronLoose_NoReta_NoW2) != 0: return False

    w2CutValue = getW2Cut(eT,absEta)
    if w2 > w2CutValue:
        return False

    REtaCutValue = getREtaCut(eT,absEta)
    if Reta <= REtaCutValue:
        return False

    return True;

#----------------------------------------------------------------------------------------
def isRobustMedium(isEM, eta, eT, Reta, w2):

    # If not robustLoose, then not robustMedium
    if not isRobustLoose(isEM,eta,eT,Reta,w2):
        return False

    return (isEM & ElectronMedium_NOReta_NoW2) == 0;

#----------------------------------------------------------------------------------------
def isRobusterTight(isEM, expectBLayer, eta, eT, Reta, w2 ):

    # If not robustMedium, then not robusterTight
    if not isRobustMedium(isEM,eta,eT,Reta,w2):
        return False

    # If robust tight with out Reta and w2 
    if (isEM & ElectronTightRobust_NoReta_NoW2) == 0:
        return True

    if ((isEM & ElectronTightRobust_NoReta_NoW2_NoConvCut) == 0) and not expectBLayer:
        return True

    return False


# Helper Functions


#---------------------------------------------------------------------------------------
# Gets the Eta bin [0-9] given the eta
def getEtaBin(eta):
    etaBins = [0.1,0.6,0.8,1.15,1.37,1.52,1.81,2.01,2.37,2.47]
    for i, etaBin in enumerate(etaBins):
        if eta < etaBin:
            return i
    return 9

#---------------------------------------------------------------------------------------
# Gets the Et bin [0-10] given the et (MeV)
def getEtBin(eT):
    GeV = 1000
    eTBins = [5*GeV,10*GeV,15*GeV,20*GeV,30*GeV,40*GeV,50*GeV,60*GeV,70*GeV,80*GeV]
  
    for i, eT_bin in enumerate(eTBins):
        if eT < eT_bin:
            return i
    return 10

# New values cut on ratio e237/e277 (rows are eT bins, columns are eta bins)
cutReta37 = [[0.700, 0.700, 0.798, 0.700, 0.700, 0.690, 0.848, 0.876, 0.870, 0.894],  # < 5
           [0.700, 0.700, 0.700, 0.700, 0.700, 0.715, 0.860, 0.880, 0.880, 0.880], # 5-10
           [0.860, 0.860, 0.860, 0.860, 0.860, 0.730, 0.860, 0.880, 0.880, 0.880],# 10-15
           [0.860, 0.860, 0.860, 0.860, 0.860, 0.740, 0.860, 0.880, 0.880, 0.880],# 15-20
           [0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900],# 20-30
           [0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900],# 30-40
           [0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900],# 40-50
           [0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900],# 50-60
           [0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900],# 60-70
           [0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900],# 70-80
           [0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900]];# 80<

#New values for cut on shower width in 2nd sampling (rows are eT bins, columns are eta bins)
cutWeta2 = [[0.014, 0.014, 0.014, 0.014, 0.014, 0.028, 0.017, 0.014, 0.014, 0.014],   # < 5 
          [0.013, 0.013, 0.014, 0.014, 0.014, 0.026, 0.017, 0.014, 0.014, 0.014],  # 5-10
          [0.013, 0.013, 0.014, 0.014, 0.014, 0.025, 0.017, 0.014, 0.014, 0.014], # 10-15
          [0.012, 0.012, 0.013, 0.013, 0.013, 0.025, 0.017, 0.014, 0.014, 0.014], # 15-20
          [0.012, 0.012, 0.012, 0.013, 0.015, 0.025, 0.015, 0.013, 0.013, 0.013], # 20-30
          [0.012, 0.012, 0.012, 0.013, 0.015, 0.025, 0.015, 0.013, 0.013, 0.013], # 30-40
          [0.012, 0.012, 0.012, 0.013, 0.015, 0.025, 0.015, 0.013, 0.013, 0.013], # 40-50
          [0.012, 0.012, 0.012, 0.013, 0.015, 0.025, 0.015, 0.013, 0.013, 0.013], # 50-60
          [0.012, 0.012, 0.012, 0.013, 0.015, 0.025, 0.015, 0.013, 0.013, 0.013], # 60-70
          [0.012, 0.012, 0.012, 0.013, 0.015, 0.025, 0.015, 0.013, 0.013, 0.013], # 70-80
          [0.012, 0.012, 0.012, 0.013, 0.015, 0.025, 0.015, 0.013, 0.013, 0.013]];# 80<;

#----------------------------------------------------------------------------------------
def getREtaCut(eT, eta):
  eTBin = getEtBin(eT)
  etaBin = getEtaBin(eta)
  return cutReta37[eTBin][etaBin]

#----------------------------------------------------------------------------------------
def getW2Cut(eT, eta):
  eTBin = getEtBin(eT)
  etaBin = getEtaBin(eta)
  return  cutWeta2[eTBin][etaBin]


