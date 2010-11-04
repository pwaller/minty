from .options import parse_options
from .utils import init_root
from .utils.logger import log_level

from logging import DEBUG, getLogger; log = getLogger("minty.main")

def main(Analysis):
    with log_level(DEBUG):
        run(Analysis)

def run(Analysis):
    from sys import argv
    options, input_tree = parse_options(argv)
        
    if options.shell_on_exception:
        from IPython.Shell import IPShellEmbed; IPShellEmbed(["-pdb"])
        
    analysis = Analysis(input_tree, options)
    analysis.run()
