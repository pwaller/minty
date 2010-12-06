
from .main import main
from .utils import init_root
init_root()

import ROOT as R
R.PyConfig.IgnoreCommandLineOptions = True

from imp import find_module
try:
    find_module("AthenaPython")
    athena_available = True
except ImportError:
    athena_available = False

if athena_available:
    from .athena import AnalysisAlgorithm, athena_setup, setup_pool_skim
else:
    from .base import AnalysisBase
