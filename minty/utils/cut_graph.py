# Plan:
# This class supports easy specification of an analysis.
# You can specify the following:
#  * cuts as "check->bool" and "dependency->bool" [and "value->num/tuple"]
#  * "value->num|tuple" histograms, with cut restrictions
#  * "value->num|tuple" histograms (X) all/some cuts
#  * object selection as "container", "


from types import FunctionType, StringType, MethodType

NA = -1

class Cut(object):
    def __init__(self, name, cut, dep=None, val=None):
        assert type(name) is StringType
        for x in (cut, dep, val):
            assert x is None or type(x) in (FunctionType, MethodType)

        self.name = name
        self.dependency = dep
        self.value = val

        if dep:
            self.cut = lambda x : NA if not dep(x) else cut(x)
        else:
            self.cut = cut

    @property
    def __call__(self, x):
        return self.cut(x)

    @property
    def bins(self):
        if self.dependency is None:
            return (self.name, 2, 0, 2)
        else:
            return (self.name, 3, -1, 2)

class Histo(object):
    def __init__(self, name, value, b, req=(), cross=(), **kwargs):
        assert type(value) in (FunctionType, MethodType)
        assert hasattr(req, "__iter__")
        self.name = name
        self.value = value
        self.requirements = list(req)
        self.cross = list(cross)
        self.binning = list(b)
        self.kwargs = kwargs

    def initialize(self, cuts, hm):
        # check that all histograms actually exist
        cut_dict = dict((cut.name, cut) for cut in cuts)
        for n in self.requirements + self.cross:
            assert n in cut_dict.keys(), "h %s - %s is not a cut" % (self, n)

        # append cross-product cuts to the axes
        self.binning += [cut_dict[x].bins for x in self.cross]
        self.filler = hm.get(self.name, b=self.binning, **self.kwargs)

    def fill(self, event, cut_results):
        for x in self.requirements:
            if not cut_results[x]:
                return
        val = list(self.value(event))
        val.extend(1.0 if cut_results[x] else 0.0 for x in self.cross)
        print val
        self.filler(*val, w = event.event_weight)

class CutGroup(object):
    def __init__(self, name, histogram_manager):
        """Initialize the cut helper with a name and a histogram manager.
        This class will use 'name' as a base path to save its results"""
        self.name = name
        self.histogram_manager = self.hm = histogram_manager
        self.cuts = []
        self.hist = []
        self.subgroups = []

    def __call__(self, obj):
        if isinstance(obj, Cut):
            self.cuts.append(obj)
        elif isinstance(obj, Histo):
            self.hist.append(obj)
        
    def add_subgroup(sg, container):
        assert isinstance(sg, CutGroup)
        self.subgroups.append((container, obj))

    def make_subgroup(name, container):
        self.add_subgroup(CutGroup("%s/%s" % (self.name, name), self.hm))

    def initialize(self, super_cuts=()):
        """Setup the CutGroup"""
        self._cut_functions = [(cut.name, cut.cut) for cut in self.cuts]
        cut_names = [cut.name for cut in self.cuts]
        self(Histo("cutflow", lambda e : (), b=(), cross=cut_names))

        for h in self.hist:
            h.initialize(self.cuts, self.hm)
        for sg in self.subgroups:
            sg.initialize(self.cuts + list(super_cuts))
        
    def execute(self, event, super_results = {}):
        # In the following, all cuts are evaluated
        results = dict([(n, f(event)) for n, f in self._cut_functions])
        results.update(super_results)
        for h in self.hist:
            h.fill(event, results)
        for container, sg in self.subgroups:
            if container == "":
                sg.execute(event, results)
            else:
                for obj in getattr(event, container):
                    sg.execute(obj, results)

