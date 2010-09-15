from minty.utils import timer
from minty.utils.grl import GRL, FakeGRL
from minty.histograms import HistogramManager
from minty.metadata import TallyManager
from minty.treedefs.egamma import egamma_wrap_tree

from logbook import Logger; log = Logger("AnalysisBase")

class DropEvent(Exception):
    pass

class AnalysisBase(object):
    def __init__(self, input_tree, options):
        self.options = options
        self.input_tree = egamma_wrap_tree(input_tree)
        self.info = self.input_tree._selarg
        
        self.setup_grl(options)
        self.setup_objects()
        
        self.histogram_manager = self.h = HistogramManager()
        self.tally_manager = TallyManager()
        
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
        from treedefs.base import EGamma
        EGamma._event = self.input_tree
        
        global_instance = tree.Global_obj._instance
        global_instance._grl = self.grl
    
    def finalize(self):
        self.histogram_manager.finalize()
        #self.tally_manager.finalize()
        
    def event(self, idx, event):
        event.index = idx
        try:
            for task in self.tasks:
                task(self, event)
        except DropEvent:
            pass
        except:
            rlum = event.RunNumber, event.LumiBlock
            print "Exception encountered in %r" % (rlum,)
            raise
        
    def run(self):
        with timer("perform analysis loop") as t:
            events = self.input_tree.loop(self.event, 
                                          lo=self.options.skip, 
                                          hi=self.options.limit)
        log.info("Looped over %i events at %.2f events/sec" % (events, events / t.elapsed))
        self.finalize()

