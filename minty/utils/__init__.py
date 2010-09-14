from __future__ import with_statement

import ROOT as R

from OQMaps import check_photon, check_electron 

def init_root():
    """
    Make ROOT init happen without it having argv, so it doesn't catch --help
    Also stop stupid duplicate warnings.
    """
    from DQUtils.ext.silence import silence_sout_serr
    import sys
    with silence_sout_serr(lambda s: "duplicate entry" in s):
        oldargv = sys.argv; sys.argv = []; R.kTRUE; sys.argv = oldargv
        
    R.TH1.SetDefaultSumw2()
    R.gStyle.SetPalette(1)

def mark_object_quality(ana, event):
    run = event.RunNumber
    
    for ph in event.photons:
        ph.good_oq = check_photon(run, ph.cl.eta, ph.cl.phi) != 3
        
    for el in event.electrons:
        el.good_oq = check_electron(run, el.cl.eta, el.cl.phi) != 3
