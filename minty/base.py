from __future__ import with_statement

from logging import getLogger; log = getLogger("minty.base")

from os.path import basename, exists
from time import time

import ROOT as R

from EnergyRescalerTool import EnergyRescaler

from minty.utils import timer, event_cache
from minty.utils.skimtree import skimtree
from minty.utils.grl import GRL, FakeGRL
from minty.histograms import HistogramManager
from minty.metadata.period import period_from_run
from minty.treedefs.egamma import egamma_wrap_tree

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
        
        self.release_16 = options.release == "rel16"
        self.project = options.project
        self.specific_events = options.events
        
        self.last_tree = 0
        
        self.options = options
        self.original_tree = input_tree
        self.tree_name = input_tree.GetName()
        self.input_tree = egamma_wrap_tree(input_tree, options)
        # Save a few attribute lookups since this is on the critical path
        get_tree = self.input_tree.tree.GetTree
        type(self).root_tree = property(lambda s: get_tree())
        self.info = self.input_tree._selarg
        
        self.setup_grl(options)
        self.setup_objects()
        
        self.result_name = options.output
        self.histogram_manager = self.h = None
        
        self.current_tree = self.current_run = self.previous_run = None
        
        self.should_dump = False
        self.events_to_dump = []
        self.tasks = []
        self.stopwatch = R.TStopwatch()
        
        self.initialize_counters()
    
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
        EGamma._v16_energy_rescaler = EnergyRescaler()
        EGamma._v16_energy_rescaler.useDefaultCalibConstants()
        
        global_instance = tree.Global_obj._instance
        global_instance._grl = self.grl
        global_instance._event = self.input_tree
    
    def get_unused_filename(self, name):
        """
        Return a file that doesn't exist yet by appending numbers to the filename
        """
        if not exists(name):
            return name
        for i in xrange(300):
            namepart = "%s.%i" % (name, i)
            if not exists(namepart):
                return namepart
        
        raise RuntimeError("Created more files than expected..")
    
    def init_result_store(self, period, run):
        """
        Create the result store. If it already exists, flush the existing one
        to disk.
        """
        log.info("Run, period changed: %s, %s", period, run)
        if self.histogram_manager and not self.options.run_specific_output:
            # Don't create a new file unless --run-specific-output specified
            return
            
        if self.histogram_manager is not None:
            self.flush()
        
        result_name = self.options.output
        if self.options.run_specific_output:
            if ".root" in result_name:
                result_name = result_name[:-len(".root")]
            result_name = result_name + "-P%s-R%i.root" % (period, run)
            
        result_name = self.get_unused_filename(result_name)
        self.histogram_manager = self.h = HistogramManager(result_name)
    
    def initialize_counters(self):
        self.exception_count = 0
        self.dumped_events = 0
        self.files_processed = []
        self.file_metadata = []
        self.stopwatch.Start()
            
    def flush(self):
        """
        Write analysis result to disk
        """
        log.info("Flushing data store..")
        hm = self.histogram_manager
        
        hm.write_parameter("exception_count", self.exception_count)
                
        this_tree = self.input_tree.tree.GetTreeNumber()
        processed_trees = this_tree - self.last_tree + 1
        self.last_tree = this_tree
        hm.write_parameter("processed_trees", processed_trees)
        hm.write_parameter("jobs_files", 1)
        
        hm.write_parameter("walltime", self.stopwatch.RealTime())
        hm.write_parameter("cputime", self.stopwatch.CpuTime())
        
        hm.write_object("file_processed_list", self.files_processed)
        hm.write_object("file_metadata", self.file_metadata)
        
        hm.finalize()
        self.initialize_counters()
    
    def dump_events(self):
        if self.events_to_dump:
            log.info("Skimming {0} events".format(len(self.events_to_dump)))
        start_skim = time()
        skimtree(self.options.dump, self.events_to_dump, self.original_tree)
        skim_time = time() - start_skim
        self.histogram_manager.write_parameter("skimtime", skim_time)
        log.info("Took {0:.3f}s to skim {1} events.".format(
                 skim_time, len(self.events_to_dump)))
    
    def finalize(self):
        if self.options.dump:
            self.dump_events()
        self.flush()
        
    def new_tree(self):
        self.files_processed.append(self.root_tree.GetDirectory().GetName())
        lumi = self.root_tree.GetDirectory().Get("Lumi/%s" % self.tree_name)
        self.file_metadata.append(lumi.GetString().Data())
        
    def event(self, idx, event):
        self.should_dump = False
        event.index = idx
        event_cache.invalidate()
        self.current_run = event.RunNumber
        if self.current_run != self.previous_run:
            self.period, (_, _) = period_from_run(self.current_run)
            self.init_result_store(self.period, self.current_run)
            
        tree = self.root_tree
        if self.current_tree != tree:
            self.new_tree()
            self.current_tree = tree
        
        try:
            for task in self.tasks:
                task(self, event)
        except DropEvent:
            pass
        except (KeyboardInterrupt, SystemExit):
            rlum = event.RunNumber, event.LumiBlock, event.index
            log.exception("Leaving code at (run, lb, idx) = %r", rlum)
            raise
        except:
            f = basename(self.current_tree.GetDirectory().GetName())
            rlum = f, event.RunNumber, event.LumiBlock, event.index
            log.exception("Exception encountered in (file, run, lb, idx) = %r", rlum)
            if self.options.shell_on_exception:
                raise
            
            self.exception_count += 1
            if self.exception_count > self.options.max_exception_count:
                raise RuntimeError("Encountered more than `max_exception_count`"
                                   " exceptions. Aborting.")
        
        if self.should_dump:
            self.events_to_dump.append(idx)
        self.previous_run = self.current_run
        
    def run(self):
        if self.specific_events:
            events = len(self.specific_events)
            log.info("Processing %i specific events..", events)
            with timer("perform analysis loop") as t:
                for i in self.specific_events:
                    self.input_tree.GetEntry(i)
                    self.event(i, self.input_tree)
            args = events, events / t.elapsed
            log.info("Looped over %i events at %.2f events/sec" % args)
            return
        
        events = min(self.input_tree.tree.GetEntries(), self.options.limit)
        log.info("Will process %i events." % events)
        with timer("perform analysis loop") as t:
            events = self.input_tree.loop(
                self.event, lo=self.options.skip, 
                hi=self.options.skip+self.options.limit)
                
        args = events, events / t.elapsed
        log.info("Looped over %i events at %.2f events/sec" % args)
        self.finalize()

