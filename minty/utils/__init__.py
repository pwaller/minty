from __future__ import with_statement

import ROOT as R

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
init_root()

from OQMaps import check_photon, check_electron

def mark_object_quality(ana, event):
    run = event.RunNumber
    
    for ph in event.photons:
        ph.good_oq = check_photon(run, ph.cl.eta, ph.cl.phi) != 3
        
    for el in event.electrons:
        el.good_oq = check_electron(run, el.cl.eta, el.cl.phi) != 3

def mark_is_grl(ana, event):
    event.is_grl = (event.RunNumber, event.LumiBlock) in ana.grl

exiting = False
@R.TPyDispatcher
def count_canvases():
    if not exiting and not get_visible_canvases():
        R.gApplication.Terminate()

def get_visible_canvases():
    return [c for c in R.gROOT.GetListOfCanvases() if not c.IsBatch()]

def wait_for_zero_canvases():
    "Wait for all canvases to be closed, or ctrl-c"
    
    # Handle ctrl-c
    sh = R.TSignalHandler(R.kSigInterrupt, True)
    sh.Add()
    sh.Connect("Notified()", "TApplication", R.gApplication, "Terminate()")
    sh.Connect("Notified()", "TROOT",        R.gROOT,        "SetInterrupt()")
    
    visible_canvases = get_visible_canvases()
    
    for canvas in visible_canvases:
        if not getattr(canvas, "_py_close_dispatcher_attached", False):
            canvas._py_close_dispatcher_attached = True
            canvas.Connect("Closed()", "TPyDispatcher",
                           count_canvases, "Dispatch()")
                           
        canvas.Update()
        
    if visible_canvases and not R.gROOT.IsBatch():
        print "There are canvases open. Waiting until exit."
        R.gApplication.Run(True)
        global exiting
        exiting = True

wait = wait_for_zero_canvases

def prevent_close_with_canvases():
    register(wait_for_zero_canvases)

def make_chain(files):
    first_file = R.TFile(files[0])
    is_pau = "PAUReco" in set(k.GetName() for k in first_file.GetListOfKeys())
    if is_pau:
        treename = "PAUReco"
    else:
        treename = "egamma"
    c = R.TChain(treename)
    for f in files:
        c.AddFile(f)
    return c
    
def event_loop(function, tree, *args, **kwargs):
    from time import time
    print "Processing", tree.tree.GetEntries(), "events"
    start = time()
    
    Nevents = tree.loop(function, *args, **kwargs)
    
    duration = time() - start
    print "Events processed:", Nevents
    print "Took %.3fs, (%.3f / sec)" % (duration, Nevents / duration)        
