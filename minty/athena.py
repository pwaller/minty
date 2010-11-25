from __future__ import with_statement

from logging import getLogger; log = getLogger("minty.base")
from glob import glob

from AthenaPython import PyAthena

import ROOT as R

from minty.utils import timer
from minty.utils.grl import GRL, FakeGRL
from minty.histograms import AthenaHistogramManager
from minty.metadata import TallyManager

def athena_setup(input = None, max_events = None):
    # use closest DB replica
    from AthenaCommon.AppMgr import ServiceMgr
    from PoolSvc.PoolSvcConf import PoolSvc
    ServiceMgr+=PoolSvc(SortReplicas=True)
    from DBReplicaSvc.DBReplicaSvcConf import DBReplicaSvc
    ServiceMgr+=DBReplicaSvc(UseCOOLSQLite=False)
    #ServiceMgr+=DBReplicaSvc(UseCOOLSQLite=True)

    # This import makes Athena read Pool files.
    import AthenaPoolCnvSvc.ReadAthenaPool 

    # setup autoconfiguration to deal also with DAODs
    from RecExConfig.RecFlags import rec
    rec.readRDO.set_Value_and_Lock(False)
    rec.readESD.set_Value_and_Lock(False)
    rec.readAOD.set_Value_and_Lock(True)
    rec.doCBNT       = False
    rec.doWriteESD   = False
    rec.doWriteAOD   = False
    rec.doAOD        = False
    rec.doWriteTAG   = False 
    rec.doPerfMon    = False
    rec.doHist       = False
    rec.doTruth      = False
    rec.LoadGeometry = True
    rec.AutoConfiguration.set_Value_and_Lock(['ProjectName', 'RealOrSim', 'FieldAndGeo', 'BeamType', 'ConditionsTag', 'DoTruth', 'BeamEnergy', 'LumiFlags', 'TriggerStream'])

    from AthenaCommon.AthenaCommonFlags import athenaCommonFlags

    if not input is None:
        # Set input
        athenaCommonFlags.FilesInput = glob("/scratch/home_lucid/ebke/Data/data10_7TeV.00155112.*/*.root*")

    if not max_events is None:
        athenaCommonFlags.EvtMax = max_events



def setup_pool_skim(filename, accept_algs, type="AOD"):
    from OutputStreamAthenaPool.MultipleStreamManager import MSMgr
    from PrimaryDPDMaker import PrimaryDPD_OutputDefinitions as dpdOutput
    stream_name = "StreamD2%sM_MINTY" % type
    stream = MSMgr.NewPoolStream(stream_name, filename)
    stream.AcceptAlgs( accept_algs )
    dpdOutput.addAllItemsFromInputExceptExcludeList( stream_name, [] )

class DropEvent(Exception):
    pass

class AnalysisAlgorithm(PyAthena.Alg):
    def __init__(self, name, options = {}):
        super(AnalysisAlgorithm,self).__init__(name)
        self.options = options
        self.histogram_manager = self.h = AthenaHistogramManager(name)
        self.exception_count = 0
        self.event_info_key = None
        self.is_mc = None
        self.tasks = []
    
    def write_parameter(self, name, value):
        self.hsvc[name] = R.TParameter(type(value))(name, value)
        
    def initialize(self):
        log.info("Initialize Minty")
        self.sg = PyAthena.py_svc("StoreGateSvc")
    
    def load_event_info(self):
        if self.event_info_key is None:
            if self.sg.contains("EventInfo", "ByteStreamEventInfo"):
                # EventInfo in data
                self.event_info_key = "ByteStreamEventInfo"
                self.is_mc = False
            elif self.sg.contains("EventInfo", "MyEvent"):
                # EventInfo in pileup monte carlo
                self.event_info_key = "MyEvent"
                self.is_mc = True
            elif self.sg.contains("EventInfo", "McEventInfo"):
                # EventInfo in pileup monte carlo
                self.event_info_key = "McEventInfo"
                self.is_mc = True
            else:
                self.sg.dump()
                raise RuntimeError("EventInfo not found in StoreGate!") 
        self.event_info = self.sg[self.event_info_key]
        self.event_number = self.event_info.event_ID().event_number()
        self.run_number = self.event_info.event_ID().run_number()
        self.lumi_block = self.event_info.event_ID().lumi_block()

    def execute(event):
        # note that "self" is named "event" here for semantic reasons
        log.info("Executing Minty")
        event.load_event_info()

        try:
            for task in self.tasks:
                task(self, event)
        except DropEvent:
            pass
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            rlum = event.run_number, event.lumi_block, event.event_number
            log.exception("Exception encountered in (run, lb, nr) = %r", rlum)
            if self.options.get("shell_on_exception", False):
                raise
            
            self.exception_count += 1
            if self.exception_count > self.options.get("max_exception_count", 100):
                raise RuntimeError("Encountered more than `max_exception_count`"
                                   " exceptions. Aborting.")
 
    def finalize(self):
        log.info("Finalizing Minty")
        self.histogram_manager.finalize()
        self.write_parameter("exception_count", self.exception_count)

