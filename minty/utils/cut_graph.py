# Plan:
# This class supports easy specification of an analysis.
# You can specify the following:
#  * cuts as "check->bool" and "dependency->bool" [and "value->num/tuple"]
#  * "value->num|tuple" histograms, with cut restrictions
#  * "value->num|tuple" histograms (X) all/some cuts
#  * object selection as "container", "


from types import FunctionType, StringType, MethodType

NA = 0 # -1

class Cut(object):
    def __init__(self, name, cut, dep=None, val=None):
        assert type(name) is StringType
        for x in (cut, dep, val):
            assert x is None or type(x) in (FunctionType, MethodType)

        self.name = name
        self.dependency = dep
        self.value = val
        self.dummy = False

        if dep:
            self.cut = lambda x : NA if not dep(x) else cut(x)
        else:
            self.cut = cut

    @property
    def bins(self):
        if self.dependency is None:
            return (2, 0, 2)
        else:
            #return (3, -1, 2) for tristate (NA == -1)
            return (2, 0, 2)

class SetContainer(Cut):
    def __init__(self, container_name, func):
        super(SetContainer, self).__init__(container_name, self.cut)
        self.f = lambda e : setattr(e, container_name, func(e))
        self.dummy = True

    def cut(self, x):
        self.f(x)
        return True

    @property
    def bins(self):
        return (1,1,2)

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

    def fill(self, obj, event, cut_results):
        for x in self.requirements:
            if not cut_results[x]:
                return
        val = self.value(obj)
        if not hasattr(val, "__iter__"):
            val = (val,)
        val = list(val)
        val.extend(1.0 if cut_results[x] else 0.0 for x in self.cross)
        self.filler(*val, **{"w": event.event_weight} )

class CutGroup(object):
    def __init__(self, name, histogram_manager, container=None):
        """Initialize the cut helper with a name and a histogram manager.
        This class will use 'name' as a base path to save its results
        If a container is specified this cutgroup will refer to
        and iterate over it"""

        self.histogram_manager = self.hm = histogram_manager
        self.name = name
        self.container = container
        self.subgroups = []
        self.sg = {}
        self.cuts = []
        self.hist = []

    def __call__(self, obj):
        if isinstance(obj, Cut):
            self.cuts.append(obj)
        elif isinstance(obj, Histo):
            self.hist.append(obj)
        
    def add_subgroup(self, sg):
        assert isinstance(sg, CutGroup)
        self.subgroups.append(sg)
        self.sg[sg.name] = sg

    def make_subgroup(self, name, container):
        cg = CutGroup("%s/%s" % (self.name, name), self.hm, container)
        self.add_subgroup(cg)
        return cg

    def initialize(self, super_cuts=()):
        """Setup the CutGroup"""
        self._cut_functions = [(cut.name, cut.cut) for cut in self.cuts]
        cut_names = [cut.name for cut in self.cuts if not cut.dummy]
        title = "cuts;%s;" % (";".join(cut_names))
        print "setting up ndim histogram crossing : %s" % cut_names
        self(Histo("%s/cuts" % self.name, lambda e : (), b=(), t=title, cross=cut_names))

        for h in self.hist:
            h.initialize(self.cuts, self.hm)
        for sg in self.subgroups:
            sg.initialize(self.cuts + list(super_cuts))

    def evaluate(self, obj, event):
        self.results = {}
        for sg in self.subgroups:
            if sg.container is None:
                sg.results = sg.execute(obj, event, results)
            else:
                objs = getattr(obj, sg.container)
                sg.results = [sg.evaluate(o, event) for o in objs]
        return dict([(n, f(obj)) for n, f in self._cut_functions])

    def fill(self, obj, event, results=None):
        if results is None:
            results = self.results
        for h in self.hist:
            h.fill(obj, event, results)
        for sg in self.subgroups:
            if sg.container is None:
                results = dict(self.results.items() + sg.results.items())
                sg.fill(obj, event, results)
            else:
                for o, res in zip(getattr(obj, sg.container), sg.results):
                    results = dict(self.results.items() + res.items())
                    sg.fill(o, event, results)

    def execute(self, event):
        self.results = self.evaluate(event, event)
        self.fill(event, event, self.results)

    def selected(self, event, name):
        sg = self.sg[name]
        results = zip(sg.results, getattr(event, sg.container))
        return [y for x, y in results if all(bool(z) == True for z in x.values())]

