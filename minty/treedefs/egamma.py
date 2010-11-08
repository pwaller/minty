from .base import (CurrentVS, VariableSelection, Global, Trigger, Vertex, 
                   Electron, Photon, TruthPhoton)
from pytuple.readtuple import make_wrapper
from pytuple.treeinfo import treeinfo as TI

def get_pau_trigger_indices(t):
    if not t.GetBranch("TriggersRun_ph"):
        return []
    t.GetEntry(0)
    return list(enumerate(t.TriggersRun_ph))

def setup_pau_trigger_info(t, tt, Trigger):
    
    class PassEF(object):
        ph = TI.int
    tt.add_list(PassEF, "PassEF", 100, **kwargs)
    
    for trig_index, trig_name in get_pau_trigger_indices(t):
        trigger_func = lambda _: tt.PassEF[trig_index].ph
        setattr(Trigger, trig_name, trigger_func)
        trig_bit = 0x1 << trig_index
        trigger_objs_func = lambda _: [p for p in tt.photons 
                                       if p.EF_matchPass & trig_bit]
        setattr(Trigger, trig_name + "_objects", trigger_objs_func)

def egamma_wrap_tree(t):
    
    leafset = set(l.GetName() for l in t.GetListOfLeaves())
    
    CurrentVS.args = selarg = VariableSelection()
    selarg.have_truth = any("truth" in l or l.endswith("MC") for l in leafset)
    selarg.tuple_type = {'PAUReco':'pau', 'egamma':'eg'}.get(t.GetName(), "eg")
    
    tt = make_wrapper(t, selarg=selarg)
    
    kwargs = dict(create=False, warnmissing=True)
    
    tt.add(Global)
    
    if selarg.tuple_type == "pau":   
       setup_pau_trigger_info(t, tt, Trigger)
    
    tt.add(Trigger, "EF", **kwargs)
    
    # Note that the L2 code is currently broken since we modify the `Trigger`
    # class for PAU.
    # tt.add(Trigger, "L2", **kwargs)
    
    tt.add_list(Vertex,      "vertices",      300, **kwargs)
    
    tt.add_list(Photon,      "photons",       300, **kwargs)
    tt.add_list(Electron,    "electrons",     300, **kwargs)
    tt.add_list(TruthPhoton, "true_photons",  300, **kwargs)
        
    return tt
