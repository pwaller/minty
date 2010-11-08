from __future__ import with_statement

from minty.utils import timer, event_cache
from minty.utils.grl import GRL, FakeGRL
from minty.histograms import HistogramManager
from minty.metadata import TallyManager
from minty.treedefs.egamma import egamma_wrap_tree

from logging import getLogger; log = getLogger("minty.base")

class DropEvent(Exception):
    pass
    
# Needed at least because we give some of the tree objects a reference to the 
# tree through their class definitions. This is a bad idea but there is no other
# "get it working now" way that I am aware of.
AnalysisSingleton = None

class AnalysisBase(object):
    def __init__(self, input_tree, options):
        global AnalysisSingleton
        assert not AnalysisSingleton
        AnalysisSingleton = self
        
        self.options = options
        self.input_tree = egamma_wrap_tree(input_tree)
        self.info = self.input_tree._selarg
        
        self.setup_grl(options)
        self.setup_objects()
        
        self.histogram_manager = self.h = HistogramManager(options.output)
        self.tally_manager = TallyManager()
        
        self.exception_count = 0
        
        # TODO
        #self.tally_manager.count("runlumi", (Run, LumiNum))
        
        self.tasks = []
    
    def setup_grl(self, options):
        if options.grl_path:
            self.grl = GRL(options.grl_path)
        else:
            self.grl = FakeGRL()
    
    def setup_objects(self):
        """
        Give objects access to information they need.
        
        sort-of hack, but I don't know how else to get this information around.
        """
        tree = self.input_tree
        from treedefs.base import EGamma, TruthPhoton
        TruthPhoton._event = EGamma._event = self.input_tree
        
        global_instance = tree.Global_obj._instance
        global_instance._grl = self.grl
    
    def write_parameter(name, type_, value):
        param = R.TParameter(type_)(name, value)
        param.Write()
    
    def finalize(self):
        log.info("Writing to %s" % self.resultname)
        f = R.TFile(self.resultname, "recreate")
        
        self.histogram_manager.finalize()
        self.write_parameter("exception_count", self.exception_count)
                
        f.Close()
        
        #self.tally_manager.finalize()
        
    def event(self, idx, event):
        event.index = idx
        event_cache.invalidate()
        try:
            for task in self.tasks:
                task(self, event)
        except DropEvent:
            pass
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            rlum = event.RunNumber, event.LumiBlock, event.index
            log.exception("Exception encountered in (run, lb, idx) = %r", rlum)
            self.exception_count += 1
            if self.exception_count > self.options.max_exception_count:
                raise RuntimeError("Encountered more than `max_exception_count`"
                                   " exceptions. Aborting."
        
    def run(self):
        events = min(self.input_tree.tree.GetEntries(), self.options.limit)
        log.info("Will process %i events." % events)
        with timer("perform analysis loop") as t:
            events = self.input_tree.loop(
                self.event, lo=self.options.skip, 
                hi=self.options.skip+self.options.limit)
                
        args = events, events / t.elapsed
        log.info("Looped over %i events at %.2f events/sec" % args)
        self.finalize()

