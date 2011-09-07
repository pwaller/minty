from __future__ import with_statement

from .options import parse_options
from .utils import init_root
from .utils.logger import log_level

from logging import DEBUG, getLogger; log = getLogger("minty.main")


def make_main(Analysis):
    def thunk():
        return main(Analysis)
    return thunk

def main(Analysis):
    with log_level(DEBUG):
        run(Analysis)

def run(Analysis):
    from sys import argv
    options, input_tree = parse_options(argv)
        
    if options.shell_on_exception:
        try:
            from IPython.Shell import IPShellEmbed
        except ImportError:
            #from IPython.frontend.terminal.embed import InteractiveShellEmbed as IPShellEmbed
            from pudb import pm
            import sys
            def f(*args):
                pm()
            sys.excepthook = f
        else:
            IPShellEmbed(["-pdb"])
        
        
    analysis = Analysis(input_tree, options)
    analysis.run()
