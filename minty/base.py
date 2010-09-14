from minty.utils.grl import GRL, FakeGRL
from minty.histograms import HistogramManager
from minty.metadata import TallyManager
from minty.treedefs.egamma import egamma_wrap_tree

class DropEvent(Exception):
    pass

class AnalysisBase(object):
    def __init__(self, input_tree, options):
        self.options = options
        self.input_tree = egamma_wrap_tree(input_tree)
        
        if options.grl_path:
            self.grl = GRL(options.grl_path)
        else:
            self.grl = FakeGRL()
        
        self.histogram_manager = self.h = HistogramManager()
        self.tally_manager = TallyManager()
        
        # TODO
        #self.tally_manager.count("runlumi", (Run, LumiNum))
        
        self.tasks = []
    
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
        self.input_tree.loop(self.event, lo=self.options.skip, hi=self.options.limit)
        self.finalize()



