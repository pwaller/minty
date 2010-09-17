from beaker.cache import CacheManager
from beaker.util import func_namespace

class EventCache(object):
    def __init__(self):
        self.manager = CacheManager()
        self.cache = self.manager.get_cache("event_cache")
        
    def __call__(self, func):
        return func
        namespace = (func_namespace(func),)
        cache = self.cache
        def trampoline(*args):
            key = namespace + tuple(hash(x) for x in args)
            return cache.get_value(key, createfunc=lambda: func(*args))
        return trampoline
        
    def invalidate(self):
        self.cache.clear()
        
event_cache = EventCache()
