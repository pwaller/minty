
from .main import main
from .utils import init_root
#init_root()

import ROOT as R
try:
    R.PyConfig.IgnoreCommandLineOptions = True
except Exception as x:
    pass

