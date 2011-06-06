from itertools import izip
from logging import getLogger; log = getLogger("minty.treedefs")

from pytuple.readtuple import make_wrapper
from pytuple.treeinfo import treeinfo as TI

from .base import (CurrentVS, VariableSelection, Global, Trigger, Vertex, 
                   Electron, Photon, TruthPhoton, Jet)
from .conditional import ConditionalMeta

def setup_pau_trigger_info(t, tt, Trigger, **kwargs):
    
    class PassTriggerPH(object):
        ph = TI.int
        
    class PassTriggerEL(object):
        el = TI.int
        
    for name, T in [("ph", PassTriggerPH), ("el", PassTriggerEL)]:
        tt.add_list(T, "PassL1%s" % name, 100, rootname="PassL1", **kwargs)
        tt.add_list(T, "PassL2%s" % name, 100, rootname="PassL2", **kwargs)
        tt.add_list(T, "PassEF%s" % name, 100, rootname="PassEF", **kwargs)
    
    class TriggerL1(Trigger): pass
    class TriggerL2(Trigger): pass
    class TriggerEF(Trigger): pass
    
    def setup_trigger_getter_ph(T, what, trig_index, trig_name):
        
        this_trigger = getattr(tt, "Pass%sph" % what)[trig_index]
        setattr(T, trig_name, property(lambda _, t=this_trigger: t.ph))
        
        ph_insts = tt.photons_list._instances
        getters = [getattr(type(ph), "%s_matchPass" % what).fget for ph in ph_insts]
        trig_bit = 0x1 << trig_index
        def trigger_objs_func(_, trig_bit=trig_bit, tt=tt, getters=getters):
            phs = izip(tt.photons, getters)
            return [p for p, matchPass in phs if not (matchPass(p) & trig_bit)]
        setattr(T, trig_name + "_photons", property(trigger_objs_func))
        
    def setup_trigger_getter_el(T, what, trig_index, trig_name):
        this_trigger = getattr(tt, "Pass%sel" % what)[trig_index]
        setattr(T, trig_name, property(lambda _, t=this_trigger: t.el))
    
    t.GetEntry(0)
    if not t.GetBranch("TriggersRun_ph"):
        el_trig_indices = ph_trig_indices = []
    else:
        ph_trig_indices = list(enumerate(t.TriggersRun_ph))
        el_trig_indices = list(enumerate(t.TriggersRun_el))
    
    print ph_trig_indices, el_trig_indices
    
    log.info("Photon trigger indices:")
    for trig_index, trig_name in ph_trig_indices:
        log.info("  %2i = %s", trig_index, trig_name)
        if trig_name[0].isdigit():
            trig_name = "_" + trig_name
            
        # Remove the normal way off accessing the leaf
    	setattr(Trigger, trig_name, None)
    
        setup_trigger_getter_ph(TriggerL1, "L1", trig_index, trig_name)
        setup_trigger_getter_ph(TriggerL2, "L2", trig_index, trig_name)
        setup_trigger_getter_ph(TriggerEF, "EF", trig_index, trig_name)
        
    log.info("Electron trigger indices:")
    for trig_index, trig_name in el_trig_indices:
        log.info("  %2i = %s", trig_index, trig_name)
        if trig_name[0].isdigit():
            trig_name = "_" + trig_name
    
        # Remove the normal way off accessing the leaf
    	setattr(Trigger, trig_name, None)
    	
        setup_trigger_getter_el(TriggerL1, "L1", trig_index, trig_name)
        setup_trigger_getter_el(TriggerL2, "L2", trig_index, trig_name)
        setup_trigger_getter_el(TriggerEF, "EF", trig_index, trig_name)
    
    return TriggerL1, TriggerL2, TriggerEF

def egamma_wrap_tree(t, options):
    
    leafset = set(l.GetName() for l in t.GetListOfLeaves())
    
    CurrentVS.args = selarg = VariableSelection()
    selarg.have_truth = any("truth" in l or l.endswith("MC") for l in leafset)
    selarg.tuple_type = {'PAUReco':'pau', 'egamma':'eg', 'photon':'ph'}.get(t.GetName(), "eg")
    
    tt = make_wrapper(t, selarg=selarg)
    
    kwargs = dict(create=False, warnmissing=True)
    
    if selarg.tuple_type == "pau":
        Global.larError = 0
            
    tt.add(Global)
    
    tt.add_list(Vertex,      "vertices",      300, **kwargs)
        
    Ph = ConditionalMeta.make_class(Photon, options.project, options.release)
    El = ConditionalMeta.make_class(Electron, options.project, options.release)
    
    if t.GetName() == "physics":
        # SMWZ: Disable jet matching
        Ph.imatchRecJet = -1
            
    tt.add_list(El,          "electrons",     400, **kwargs)
    tt.add_list(Ph,          "photons",       400, **kwargs)
    tt.add_list(Jet,         "jets",          400, **kwargs)
    tt.add_list(TruthPhoton, "true_photons",  400, **kwargs)
    
    if selarg.tuple_type == "pau":   
        trigger_classes = setup_pau_trigger_info(t, tt, Trigger, **kwargs)
        TriggerL1, TriggerL2, TriggerEF = trigger_classes
    else:
        TriggerL1 = TriggerL2 = TriggerEF = Trigger
        
    tt.add(TriggerL1, "L1", **kwargs)
    tt.add(TriggerL2, "L2", **kwargs)
    tt.add(TriggerEF, "EF", **kwargs)
    
    if selarg.tuple_type == "pau":
        # larError not defined for PAU.
        tt.larError = 0
        
    return tt
