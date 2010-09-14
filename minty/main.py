from .options import parse_options
from .utils import init_root

def main(Analysis):
    from sys import argv
    options, input_tree = parse_options(argv)
        
    if options.shell_on_exception:
        from IPython.Shell import IPShellEmbed; IPShellEmbed(["-pdb"])
        
    analysis = Analysis(input_tree, options)
    analysis.run()
