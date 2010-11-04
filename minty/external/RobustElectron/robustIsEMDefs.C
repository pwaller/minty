#include "egammaPIDdefs.h"

#include <iostream>
#include <iomanip>
#include <cmath>

using namespace std;

/**
   Author John Alison <johnda@sas.upenn.edu>

   Note:
   - Currently the MC mismodels the Reta and w2 distributions. 
     We redefine the isEM definitions such that the Reta and w2 cuts are loosened to recover data/MC 
     agreement in electron efficiency. 
     isRobustLoose, isRobustMedium, and isRobusterTight, address this problem.    

     The changes to the cut values are:

     eT < 5 GeV:
       - w2: 0.014 |eta| > 1.81
       - REta: 0.7 for |eta| < 1.37,   
               {0.848, 0.876, 0.870, 0.880} for |eta| bins {1.52,1.81,2.01,2.37,2.47}  

     5 <= eT < 10 GeV:
       - w2: 0.014 |eta| > 1.81
       - REta: 0.7 for |eta| < 1.37,   
               {0.860, 0.880} for |eta| bins {1.52,1.81,2.47}  

     10 <= eT < 20 GeV:
       - w2: 0.014 |eta| > 1.81
       - REta: 0.86 for |eta| < 1.37,   
               {0.860, 0.880} for |eta| bins {1.52,1.81,2.47}  
     
     eT >= 20 GeV:
       - REta 0.9 for all |eta|
       - w2 0.013 for |eta| > 1.81, default otherwise

             
   - In addition, if a standard-isEM tight electron candidate crosses a disabled BLayer module 
     the candidate is kept tight,
     despite having no BLayer hit.  
     The conversion flag is set if the electron is recovered as a conversion. 
     This recovery procedure however does not yet check the status of the crossed BLayer. 
     Thus tight electrons crossing disabled BLayers will be recovered as single track conversions
     and the isConv bit will be set, which means they will not satisfy the standard-isEM tight criteria.
     isRobusterTight resolves this problem as well.
   
  Usage:
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

     They return true if:
       isRobustLoose
       - electron satisfies the Loose cuts with new REta and w2 cut values 
       isRobustMedium
       - electron satisfies the isRobustLoose and Medium cuts 
       isRobusterTight
       - electron satisfies the isRobustMedium and tight cuts EXCEPT DPhi DEta.
          or
       - electron satisfies the isRobustMedium and tight cuts EXCEPT DPhi DEta, and the isConv flag
          AND no BLayer hit is expected

     They return false otherwise.
  

*/

bool isRobustLoose(long isEM, float eta, float eT, float Reta, float w2 );
bool isRobustMedium(long isEM, float eta, float eT, float Reta, float w2 );
bool isRobusterTight(long isEM, bool expectBLayer, float eta, float eT, float Reta, float w2 );
//   NOTE: ROBUST TIGHT IS DEPRECATED. 
//   It is strongly recommended to use robusterTight. 
//   robustTight is included here only for back compatibility/comparison
bool isRobustTight(long isEM, bool expectBLayer);

// Helper Functions

//---------------------------------------------------------------------------------------
// Gets the Reta cut given eT (MeV) and eta
float getREtaCut(float eT, float eta);

//---------------------------------------------------------------------------------------
// Gets the w2 cut given eT (MeV) and eta
float getW2Cut(float eT, float eta);

//---------------------------------------------------------------------------------------
// Gets the Eta bin [0-9] given the eta
unsigned int getEtaBin(float eta);

//---------------------------------------------------------------------------------------
// Gets the Et bin [0-10] given the et (MeV)
unsigned int getEtBin(float eT);

//---------------------------------------------------------------------------------------
// Gets the Eta bin [0-9] given the eta
unsigned int getEtaBin(float eta){
  const unsigned int nEtaBins = 10;
  const float etaBins[nEtaBins] = {0.1,0.6,0.8,1.15,1.37,1.52,1.81,2.01,2.37,2.47};
  
  for(unsigned int etaBin = 0; etaBin < nEtaBins; ++etaBin){
    if(eta < etaBins[etaBin])
      return etaBin;
  }
  
  return 9;
}

//---------------------------------------------------------------------------------------
// Gets the Et bin [0-10] given the et (MeV)
unsigned int getEtBin(float eT){
  const unsigned int nEtBins = 11;
  const float GeV = 1000;
  const float eTBins[nEtBins] = {5*GeV,10*GeV,15*GeV,20*GeV,30*GeV,40*GeV,50*GeV,60*GeV,70*GeV,80*GeV};
  
  for(unsigned int eTBin = 0; eTBin < nEtBins; ++eTBin){
    if(eT < eTBins[eTBin])
      return eTBin;
  }
  
  return 10;
}

//----------------------------------------------------------------------------------------
float getREtaCut(float eT, float eta){
  // New values cut on ratio e237/e277 (rows are eT bins, columns are eta bins)
  const float cutReta37[11][10] = {{ 0.700, 0.700, 0.798, 0.700, 0.700, 0.690, 0.848, 0.876, 0.870, 0.894}  // < 5
				   ,{0.700, 0.700, 0.700, 0.700, 0.700, 0.715, 0.860, 0.880, 0.880, 0.880} // 5-10
				   ,{0.860, 0.860, 0.860, 0.860, 0.860, 0.730, 0.860, 0.880, 0.880, 0.880}// 10-15
				   ,{0.860, 0.860, 0.860, 0.860, 0.860, 0.740, 0.860, 0.880, 0.880, 0.880}// 15-20
				   ,{0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900}// 20-30
				   ,{0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900}// 30-40
				   ,{0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900}// 40-50
				   ,{0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900}// 50-60
				   ,{0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900}// 60-70
				   ,{0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900}// 70-80
				   ,{0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900, 0.900}};// 80<

  unsigned int eTBin = getEtBin(eT);
  unsigned int etaBin = getEtaBin(eta);

  return cutReta37[eTBin][etaBin];
}

//----------------------------------------------------------------------------------------
float getW2Cut(float eT, float eta){
  
  //New values for cut on shower width in 2nd sampling (rows are eT bins, columns are eta bins)
  const float cutWeta2[11][10] = {{ 0.014, 0.014, 0.014, 0.014, 0.014, 0.028, 0.017, 0.014, 0.014, 0.014}   // < 5 
				  ,{0.013, 0.013, 0.014, 0.014, 0.014, 0.026, 0.017, 0.014, 0.014, 0.014}  // 5-10
				  ,{0.013, 0.013, 0.014, 0.014, 0.014, 0.025, 0.017, 0.014, 0.014, 0.014} // 10-15
				  ,{0.012, 0.012, 0.013, 0.013, 0.013, 0.025, 0.017, 0.014, 0.014, 0.014} // 15-20
				  ,{0.012, 0.012, 0.012, 0.013, 0.015, 0.025, 0.015, 0.013, 0.013, 0.013} // 20-30
				  ,{0.012, 0.012, 0.012, 0.013, 0.015, 0.025, 0.015, 0.013, 0.013, 0.013} // 30-40
				  ,{0.012, 0.012, 0.012, 0.013, 0.015, 0.025, 0.015, 0.013, 0.013, 0.013} // 40-50
				  ,{0.012, 0.012, 0.012, 0.013, 0.015, 0.025, 0.015, 0.013, 0.013, 0.013} // 50-60
				  ,{0.012, 0.012, 0.012, 0.013, 0.015, 0.025, 0.015, 0.013, 0.013, 0.013} // 60-70
				  ,{0.012, 0.012, 0.012, 0.013, 0.015, 0.025, 0.015, 0.013, 0.013, 0.013} // 70-80
				  ,{0.012, 0.012, 0.012, 0.013, 0.015, 0.025, 0.015, 0.013, 0.013, 0.013}};// 80<;

  unsigned int eTBin = getEtBin(eT);
  unsigned int etaBin = getEtaBin(eta);
    
  return  cutWeta2[eTBin][etaBin];
}


//----------------------------------------------------------------------------------------
bool isRobustLoose(long isEM, float eta, float eT, float Reta, float w2 ){

  float absEta = fabs(eta);
  
  // Does it pass the loose isEM with Reta and w2 removed?
  const unsigned int CALOMIDDLE_ELECTRON_NoReta_NoW2 = 0x1 << egammaPID::ClusterMiddleEnergy_Electron;
  const unsigned int ElectronLoose_NoReta_NoW2 = CALOMIDDLE_ELECTRON_NoReta_NoW2 | egammaPID::HADLEAKETA_ELECTRON;
  if((isEM & ElectronLoose_NoReta_NoW2) != 0){
    return false;
  }
  
  float w2CutValue = getW2Cut(eT,absEta);
  if(w2 > w2CutValue)
    return false;

  float REtaCutValue = getREtaCut(eT,absEta);
  if(Reta <= REtaCutValue)
    return false;

  return true;
}


//----------------------------------------------------------------------------------------
bool isRobustMedium(long isEM, float eta, float eT, float Reta, float w2 ){

  // If not robustLoose, then not robustMedium
  if(!isRobustLoose(isEM,eta,eT,Reta,w2))
    return false;

  const unsigned int CALOMIDDLE_ELECTRON_NoReta_NoW2 = 0x1 << egammaPID::ClusterMiddleEnergy_Electron;
  
  const unsigned int CALO_ELECTRON_NoReta_NoW2 = 
    egammaPID::HADLEAKETA_ELECTRON | 
    egammaPID::CALOSTRIPS_ELECTRON | 
    CALOMIDDLE_ELECTRON_NoReta_NoW2 ;

  const unsigned int ElectronMedium_NOReta_NoW2 = 
    CALO_ELECTRON_NoReta_NoW2 | 
    egammaPID::TRACKINGNOBLAYER_ELECTRON | 
    egammaPID::TRACKMATCHDETA_ELECTRON;
  

  return ((isEM & ElectronMedium_NOReta_NoW2) == 0);
}

//----------------------------------------------------------------------------------------
bool isRobusterTight(long isEM, bool expectBLayer, float eta, float eT, float Reta, float w2 ){

  // If not robustMedium, then not robusterTight
  if(!isRobustMedium(isEM,eta,eT,Reta,w2))
    return false;
  
  const unsigned int CALOMIDDLE_ELECTRON_NoReta_NoW2 = 0x1 << egammaPID::ClusterMiddleEnergy_Electron;
  
  const unsigned int CALO_ELECTRON_NoReta_NoW2 = 
    egammaPID::HADLEAKETA_ELECTRON | 
    egammaPID::CALOSTRIPS_ELECTRON | 
    CALOMIDDLE_ELECTRON_NoReta_NoW2 ;  
  
  const unsigned int ElectronTightRobust_NoReta_NoW2 = 
    CALO_ELECTRON_NoReta_NoW2 | 
    egammaPID::TRACKING_ELECTRON | 
    0x1 << egammaPID::TrackMatchEta_Electron | 
    0x1 << egammaPID::TrackMatchEoverP_Electron | 
    0x1 << egammaPID::TrackA0Tight_Electron |
    0x1 << egammaPID::ConversionMatch_Electron |
    egammaPID::TRT_ELECTRON ;

  
  // If robust tight with out Reta and w2 
  if((isEM & ElectronTightRobust_NoReta_NoW2) == 0){
    return true;
  }

  // Tight without the conversion requirement 
  const unsigned int ElectronTightRobust_NoReta_NoW2_NoConvCut = 
    CALO_ELECTRON_NoReta_NoW2 | 
    egammaPID::TRACKING_ELECTRON | 
    0x1 << egammaPID::TrackMatchEta_Electron | 
    0x1 << egammaPID::TrackMatchEoverP_Electron | 
    0x1 << egammaPID::TrackA0Tight_Electron |
    egammaPID::TRT_ELECTRON ;


  if( ((isEM & ElectronTightRobust_NoReta_NoW2_NoConvCut) == 0) && !expectBLayer){
    return true;
  }

  return false;
}



/**
   Author John Alison <johnda@sas.upenn.edu>

   NOTE: ROBUST TIGHT IS DEPRECATED. 
   It is strongly recommended to use robusterTight. 
   robustTight is included here for back compatibility

   
   Redefine Tight (RobustTight) such that the conversion flag does not veto tight
   electrons b/c they passed a disabled BLayer module. Also remove the DPhi and DEta (tight)
   cuts track-cluster matching.  
   
   Note: 
   Currently if a tight electron candidate crosses a disabled BLayer module the candidate is kept tight,
   despite having no BLayer hit.  
   The conversion flag is set if the electron is recovered as a conversion. 
   This recovery procedure however does not yet check the status of the crossed BLayer. 
   Thus tight electrons crossing disabled BLayers will be recovered as single track conversions
   and the isConv bit will be set, which means they will not satisfy the "new tight" criteria.
   isRobustTight resolves this problem.

   It has been shown that Misalignments and Detector distortions present in the data are leading to 
   degraded signal/Bkg seperation in the DPhi / DEta Trk-cluster matching variables. For the short term
   it has been decided to redefine tight such that the DEta(tight) and DPhi cuts are not applied.

   Usage:
   The isRobustTight method takes the electron isEM bitmask and a bool indicating if we expect a BLayer hit.
   It returns true if:
        - the electron satisfies the new tight requirements EXCEPT DPhi DEta.
	- the electron satisfies all the above requirements EXCEPT the isConv flag, 
            AND no BLayer hit is expected 
	
   It returs false otherwise.

*/
bool isRobustTight(long isEM, bool expectBLayer){

  // Define a bit mask for tight which excludes DPhi and DEta (tight) (The medium DEeta cut is still applied) 
  const unsigned int TRACKMATCH_NODPHI_ELECTRON = 0x1 << egammaPID::TrackMatchEta_Electron | 0x1 << egammaPID::TrackMatchEoverP_Electron  ;
  const unsigned int TRACKMATCHTIGHT_NODETA_ELECTRON = 0x1 << egammaPID::TrackA0Tight_Electron;
  const unsigned int ElectronTightRobust = egammaPID::CALO_ELECTRON | egammaPID::TRACKING_ELECTRON | TRACKMATCH_NODPHI_ELECTRON | TRACKMATCHTIGHT_NODETA_ELECTRON | egammaPID::CONVMATCH_ELECTRON | egammaPID::TRT_ELECTRON ;

  // If new tight return true
  if((isEM & ElectronTightRobust) == 0){
    return true;
  }
      
  // If all tight cuts are satisfied (minus isConv) and we dont expect a BLayer hit, return true
  const unsigned int ElectronTightRobust_NoConvCut = egammaPID::CALO_ELECTRON | egammaPID::TRACKING_ELECTRON | TRACKMATCH_NODPHI_ELECTRON | TRACKMATCHTIGHT_NODETA_ELECTRON | egammaPID::TRT_ELECTRON ;
  if( ((isEM & ElectronTightRobust_NoConvCut) == 0) && !expectBLayer){
    return true;
  }
    
  return false;
}
