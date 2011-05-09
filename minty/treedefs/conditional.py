"""
This file encapsulates logic to define conditionally-defined functions.
The aim is to avoid runtime overhead, and to keep all definitions for a class
near each other.

Not implemented:
    * Chaining conditionals
    * Any kind of protection against matching multiple conditionals
"""

from types import FunctionType

def get_name(what):
    """
    Get the function name
    """
    if isinstance(what, property):
        return what.fget.__name__
    elif isinstance(what, FunctionType):
        return what.__name__

class ConditionalMeta(type):
    """
    Types having this as the metaclass can conditionally define functions with
    a Conditional object decorator
    """
    
    # Functions are stored in this dictionary by Conditional objects. Otherwise
    # they are over-written by subsequent redefinition
    temp_store = {}

    def __new__(cls, name, bases, dct):
        """
        Create a new class. This is called at the end of a class definition.
        The purpose is to take whatever is in temp_store (inserted by 
        Conditional), and record it in the new classes' _ConditionalMeta__extra.
        Those functions are conditionally attached to the class (actually a
        new one) later in ConditionalMeta.make_class.
        
        This function has an additional check to make sure we didn't write
            @property
            @Conditional
            def func
        , because that screws everything up and might be hard to detect.
        """
        extra = dct["_ConditionalMeta__extra"] = cls.temp_store.copy()
        cls.temp_store.clear()
        
        for condition, funcs in sorted(extra.iteritems()):
            for func in funcs:
                # Check for @property @Conditional
                func_name = get_name(func)
                class_func = dct.get(func_name, None)
                is_placeholder = get_name(class_func) == "conditionalmeta_placeholder"
                if (isinstance(class_func, property) and not is_placeholder):
                    # Check that we didn't do something stupid.
                    raise RuntimeError("@Conditional should always appear "
                                       "BEFORE @property. Not true for "
                                       "@Conditional('%s')<%s.%s>." 
                                       % (condition, name, func_name))
                elif is_placeholder:
                    # Record the class name on the placeholder, so we can give
                    # nice(r) error messages.
                    if isinstance(class_func, property):
                        class_func = class_func.fget
                    class_func.__class_name = name
        
        return type.__new__(cls, name, bases, dct)
        
    def __init__(cls, name, bases, dct):
        super(ConditionalMeta, cls).__init__(name, bases, dct)
        
    @classmethod
    def make_class(cls, target, *conditions):
        """
        Instantiate the `target` class, with functions defined in `*conditions`.
        """
        if not issubclass(target, HasConditionals):
            raise RuntimeError("It only makes sense to make_class on a class "
                               "inheriting from HasConditionals.")
        
        dct = target.__dict__.copy()
        for condition in conditions:
            for function in target.__extra[condition]:
                func_name = get_name(function)
                dct[func_name] = function
            
        return type.__new__(cls, target.__name__, target.__bases__, dct)

class HasConditionals(object):
    """
    Types with conditionals should inherit from this.
    """
    __metaclass__ = ConditionalMeta

class Conditional(object):
    """
    Defines a condition. Functions decorated with Conditional("x") are only used
    if the class is "made" with ConditionalMeta.make_class(cls, "x"...)
    """
    def __init__(self, name):
        self.name = name
    
    def __call__(self, function):
        """
        Wrap a function. Record it in ConditionalMeta.temp_store and return a
        placeholder function which throws an error if it is called.
        """
        ConditionalMeta.temp_store.setdefault(self.name, []).append(function)
        def conditionalmeta_placeholder(*args, **kwargs):
            classname = conditionalmeta_placeholder._ConditionalMeta__class_name
            raise RuntimeError("This function is only callable if instantiated "
                               "with ConditionalMeta.make_class(%s, "
                               "<matching conditions>)" % classname)
        if isinstance(function, property):
            return property(conditionalmeta_placeholder)
        return conditionalmeta_placeholder

data10 = Conditional("data10")


def test():
    """
    I am here.. RuntimeError caught.
    2010 photon says: 1
    data10 test called.
    2011 photon says: 2
    Traceback (most recent call last):
      File "conditional.py", line 125, in <module>
        ph.test()
      File "conditional.py", line 89, in conditionalmeta_placeholder
        "<matching conditions>)" % classname)
    RuntimeError: This function is only callable if instantiated with ConditionalMeta.make_class(Photon, <matching conditions>)
    """
    
    class Photon(HasConditionals):
        @Conditional("data10")
        @property
        def value(self):
            return 1
        
        @Conditional("data10")
        def test(self):
            print "data10 test called."
        
        @Conditional("data11")
        @property
        def value(self):
            return 2

    plain_photon = Photon()
    try:
        print "I am here..", plain_photon.value
    except RuntimeError:
        print "RuntimeError caught."

    Photon10 = ConditionalMeta.make_class(Photon, "data10")
    Photon11 = ConditionalMeta.make_class(Photon, "data11")

    ph = Photon10()
    print "2010 photon says:", ph.value
    ph.test()
    
    ph = Photon11()
    print "2011 photon says:", ph.value
    ph.test()

    
if __name__ == "__main__":
    test()
