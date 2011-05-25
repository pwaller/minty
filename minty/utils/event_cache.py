from functools import wraps

def func_namespace(func):
    """Generates a unique namespace for a function"""
    kls = None
    if hasattr(func, 'im_func'):
        kls = func.im_class
        func = func.im_func

    if kls:
        return '%s.%s' % (kls.__module__, kls.__name__)
    else:
        return '%s.%s' % (func.__module__, func.__name__)
                                                              
class EventCache(object):
    def __init__(self):
        self.store = {}

    def get_value(self, key, createfunc):
        if not key in self.store:
            self.store[key] = createfunc()
        return self.store[key]
        
    def __call__(self, func):
        namespace = (func_namespace(func),)
        @wraps(func)
        def trampoline(*args):
            key = namespace + tuple(hash(x) for x in args)
            return self.get_value(key, createfunc=lambda: func(*args))
        return trampoline
        
    def invalidate(self):
        self.store.clear()
        
event_cache = EventCache()
