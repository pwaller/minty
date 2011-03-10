from ROOT import gROOT
from pkg_resources import resource_filename

from inspect import stack, getmodule

def get_caller_module():
    """
    Returns the module from which the caller of this function was called.
    """
    st = stack(0)
    frame, _, _, _, _, _ = st[2]
    module = getmodule(frame)
    return module

def deferred_root_loader(cpp_code, symbol):
    caller_module = get_caller_module()
    class DeferredLoader(object):
        def __call__(self, *args, **kwargs):
            
            gROOT.LoadMacro(resource_filename(caller_module.__name__, cpp_code))
            
            import ROOT
            DeferredLoader.actual_symbol = getattr(ROOT, symbol)
            
            class DeferredLoader_loaded(object):
                __call__ = staticmethod(DeferredLoader.actual_symbol)
                
            DeferredLoader_loaded.__name__ = DeferredLoader.__name__
            self.__class__ = DeferredLoader_loaded
            
            # Not a recursive call because we just replaced ourselves!
            return self.__call__(*args, **kwargs)
    
    return DeferredLoader()
