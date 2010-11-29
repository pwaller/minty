
class EventCache(object):
    def __init__(self):
        self.store = {}

    def get_value(self, key, createfunc):
        if not key in self.store:
            self.store[key] = createfunc()
        return self.store[key]
        
    def __call__(self, func):
        return func
        namespace = (func_namespace(func),)
        def trampoline(*args):
            key = namespace + tuple(hash(x) for x in args)
            return self.get_value(key, createfunc=lambda: func(*args))
        return trampoline
        
    def invalidate(self):
        self.store.clear()
        
event_cache = EventCache()
