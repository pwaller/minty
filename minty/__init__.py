
from .main import main
from .base import AnalysisBase
from .utils import init_root
init_root()

import ROOT as R
R.PyConfig.IgnoreCommandLineOptions = True

