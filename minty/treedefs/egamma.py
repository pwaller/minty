from .base import (CurrentVS, VariableSelection, Global, Trigger, Vertex, 
                   Electron, Photon, TruthPhoton)
from pytuple.readtuple import make_wrapper
from pytuple.treeinfo import treeinfo as TI

def egamma_wrap_tree(t):

    if t.GetBranch("TriggersRun_ph"):
        t.GetEntry(0)
        g10_loose_id = list(t.TriggersRun_ph).index("g10_loose")
        print "got id from TriggersRun_ph"
    else:
        g10_loose_id = 3
    print "Using g10_loose id:", g10_loose_id
    
    leafset = set(l.GetName() for l in t.GetListOfLeaves())
    
    CurrentVS.args = selarg = VariableSelection()
    selarg.have_truth = any("truth" in l or l.endswith("MC") for l in leafset)
    selarg.tuple_type = {'PAUReco':'pau', 'egamma':'eg'}.get(t.GetName(), "eg")
    
    tt = make_wrapper(t, selarg=selarg)
    
    kwargs = dict(create=False, warnmissing=True)
    
    tt.add(Global)
    
    if selarg.tuple_type == "pau":
        class PassEF(object):
            ph = TI.int
        tt.add_list(PassEF, "PassEF", 25, **kwargs)
        Trigger.g10_loose = property(lambda _: tt.PassEF[g10_loose_id].ph)
    
    tt.add(Trigger, "EF", **kwargs)
    tt.add(Trigger, "L2", **kwargs)
    
    tt.add_list(Vertex,      "vertices",      300, **kwargs)
    
    tt.add_list(Photon,      "photons",       300, **kwargs)
    tt.add_list(Electron,    "electrons",     300, **kwargs)
    tt.add_list(TruthPhoton, "true_photons",  300, **kwargs)
        
    return tt
