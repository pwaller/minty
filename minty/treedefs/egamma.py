from .base import CurrentVS, VariableSelection, Global, Trigger, Vertex, Electron, Photon
from pytuple.readtuple import make_wrapper
from pytuple.treeinfo import treeinfo as TI

def egamma_wrap_tree(t):
    
    leafset = set(l.GetName() for l in t.GetListOfLeaves())
    
    CurrentVS.args = selarg = VariableSelection()
    selarg.have_truth = any("truth" in l for l in leafset)
    selarg.tuple_type = {'PAUReco':'pau', 'egamma':'eg'}.get(t.GetName(), "eg")
    
    tt = make_wrapper(t, selarg=selarg)
    
    tt.add(Global)
    
    if selarg.tuple_type == "pau":
        class PassEF(object):
            ph = TI.int
        tt.add_list(PassEF, "PassEF", 9)
        Trigger.g10_loose = property(lambda _: tt.PassEF[3].ph)
    
    tt.add(Trigger, "EF", create=False, warnmissing=True)
    tt.add(Trigger, "L2", create=False, warnmissing=True)
    
    tt.add_list(Vertex,   "vertices",      300, create=False, warnmissing=True)
    
    tt.add_list(Photon,   "photons",       300, create=False, warnmissing=True)
    tt.add_list(Electron, "electrons",     300, create=False, warnmissing=True)
        
    return tt
