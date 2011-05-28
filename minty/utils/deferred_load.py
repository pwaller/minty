
from commands import getstatusoutput
from os import environ, listdir
from os.path import isdir
from pkg_resources import resource_filename, get_provider

from inspect import stack, getmodule

from ROOT import gROOT, gSystem

def get_caller_module():
    """
    Returns the module from which the caller of this function was called.
    """
    st = stack(0)
    frame, _, _, _, _, _ = st[2]
    module = getmodule(frame)
    return module

global python_include_path # Only set me once, so that it only ends up in the path once!
python_include_path = None

def get_python_include_path():
    status, output = getstatusoutput("python-config --includes")
    if status:
        # Something went wrong, try to resolve it. Walk up the path until we 
        # find something
        
        print "Python interpreter possibly broken? Trying other things in the path."
        
        paths = environ["PATH"].split(":")
        for path in paths:
            if not isdir(path): 
                continue
                
            if "python-config" in listdir(path):
                status, output = getstatusoutput("%s/python-config --includes" % path)
                if not status:
                    print "Found a working python interpreter:", output
                    break
                    
        assert not status, "Couldn't find working python-config"

    return output

def deferred_root_loader(cpp_code, symbol):
    """
    Load a name from ROOT when it is first called
    """
    caller_module = get_caller_module()
    caller_module_name = caller_module.__name__
    def loadmacro():
        # Beware, python-config not available on the grid, arg!
        #global python_include_path
        #if python_include_path is None:
            #python_include_path = get_python_include_path()
            #if python_include_path:
                #gSystem.AddIncludePath(python_include_path)
        gROOT.LoadMacro(resource_filename(caller_module_name, cpp_code))
    
    class DeferredLoader(object):
        def __call__(self, *args, **kwargs):
            
            try:
                loadmacro()
            except RuntimeError as e:
                message = e.args[0]
                if "Failed to load Dynamic link library" not in message:
                    print "Failing.."
                    raise
                import re
                match = re.match(r'^\(file "([^"]+)", line.*$', message)
                (f,) = match.groups()
                
                # Delete it and try again.
                from os import unlink
                print "Deleting", f, ".."
                unlink(f)
                
                loadmacro()
            
            import ROOT
            DeferredLoader.actual_symbol = getattr(ROOT, symbol)
            
            class DeferredLoader_loaded(object):
                __call__ = staticmethod(DeferredLoader.actual_symbol)
                
            DeferredLoader_loaded.__name__ = DeferredLoader.__name__
            self.__class__ = DeferredLoader_loaded
            
            # Not a recursive call because we just replaced ourselves!
            return self.__call__(*args, **kwargs)
    
    return DeferredLoader()
    
def make_deferred_instance(cls, initialization=None):
    """
    Load an instance when one of its methods is first called.
    
    Note, this only works for callable attributes, not other members or properties.
    
    For example:
    
    theOQ = make_deferred_instance(egammaOQ)
    theOQ # instance of DeferredInstance
    theOQ.x # DeferredAttribute is returned
    theOQ.x() # egammaOQ gets instantiated here
    theOQ # now an instance of egammaOQ
    theOQ.y() # first instantiation of egammaOQ is used
    """
    class DeferredInstance(object):
        instance = None
        
        deferred_attributes = []
        
        class DeferredAttribute(object):
            def __init__(self, deferred_instance, attr_name):
                self.deferred_instance = deferred_instance
                self.attr_name = attr_name
                
            def update(self, instance):
                """
                Called when an instance is created
                """
                try:
                    wrapped_func = getattr(instance, self.attr_name)
                except AttributeError:
                    print "! Wrapped class doesn't have", self.attr_name
                    raise
                
                class DeferredAttribute_loaded(object):
                    # Make a bound method (with the class instance effectively 
                    # 'curried') a static method of this class.
                    __call__ = staticmethod(wrapped_func)
                self.__class__ = DeferredAttribute_loaded
                
            def __call__(self, *args, **kwargs):
                """
                This function will only get called once, for the first call of 
                any DeferredAttribute
                """
                # Cause all of the deferred attributes to get loaded
                self.deferred_instance.instantiate()
                # Not a recursive call because our class just changed 
                # during the above call
                return self.__call__(*args, **kwargs)
        
        def instantiate(self):
            """
            Create an instance of the class and update all attributes.
            """
            if initialization:
                self.instance = initialization(cls)
            else:
                self.instance = cls()
                
            for deferred_attribute in self.deferred_attributes:
                deferred_attribute.update(self.instance)
            
        def __getattr__(self, what):
            """
            Forward requests for methods, or defer them if we aren't yet 
            instantiated.
            """
            if self.instance is None:
                attr = self.DeferredAttribute(self, what)
                self.deferred_attributes.append(attr)
                return attr
            return getattr(self.instance, what)
        
    return DeferredInstance()
