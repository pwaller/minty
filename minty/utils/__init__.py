from __future__ import with_statement

print "In utils"

import ROOT as R

from contextlib import contextmanager
from time import time

from logging import getLogger

print "Finished utils imports"
from .event_cache import event_cache

time_logger = getLogger("minty.utils.timer")
@contextmanager
def timer(what):
    start = time()
    class Timer(object):
        _elapsed = None
        @property
        def elapsed(self):
            if self._elapsed:
                return self._elapsed
            return time() - start
    timer = Timer()
    try:
        yield timer
    finally:
        timer._elapsed = time() - start
        time_logger.info("Took %.3f to %s" % (timer.elapsed, what))

@contextmanager
def canvas(*args):
    old_canvas = R.gPad.func()
    c = R.TCanvas(*args)
    c.cd()
    try:
        yield c
    finally:
        if old_canvas and getattr(old_canvas, "cd", None):
            old_canvas.cd()
        
        

def init_root():
    """
    Make ROOT init happen without it having argv, so it doesn't catch --help
    Also stop stupid duplicate warnings.
    """
    if False:
        from DQUtils.ext.silence import silence_sout_serr
        import sys
        with silence_sout_serr(lambda s: "duplicate entry" in s):
            oldargv = sys.argv; sys.argv = []; R.kTRUE; sys.argv = oldargv
    
    # Help ROOT's memory management
    creating_functions = [
        R.TH2.ProjectionX, R.TH2.ProjectionY, R.TH3.ProjectionZ,
        R.THnSparse.Projection,
    ]
    for func in creating_functions: func._creates = 1
    
    R.TH1.SetDefaultSumw2()
    R.gStyle.SetPalette(1)

exiting = False

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
    
    @R.TPyDispatcher
    def count_canvases():
        if not exiting and not get_visible_canvases():
            R.gApplication.Terminate()
            
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
    first_file = R.TFile.Open(files[0])
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
