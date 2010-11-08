
from optparse import OptionParser
from .utils import make_chain
from os import listdir
from os.path import isdir, isfile
from sys import stderr
from pprint import pformat

from logging import getLogger; log = getLogger("minty.options")

def load_files(files):
    
    actual_files = []
    using_comma_workaround = using_newline_workaround = False
    for filename in files:
        
        if isdir(filename):
            actual_files.extend(filename + "/" + f for f in listdir(filename) 
                                if ".root" in f.lower())
                                
        elif filename.endswith(".txt"):
            fromtxt = map(str.strip, open(filename).read().strip().split("\n"))
            actual_files.extend(load_files(fromtxt))
        
        else:
            # UGLY WORKAROUND.
            # This deals with a bug on the grid where "\n" ended up in the
            # input.txt file rather than \n. This should get removed some time.
            if r"\n" in filename:
                using_newline_workaround = True
            actual_files.extend(filename.split(r"\n"))
    
    real_actual_files = []
    for filename in actual_files:
        if "," in filename:
            using_comma_workaround = True
        real_actual_files.extend(filename.split(","))
    
    if using_newline_workaround:
        log.warn(r"Using workaround. input.txt lines contain '\n'")
        
    if using_comma_workaround:
        log.warn(r"Using workaround. input.txt contains comma separated files.")
    
    return real_actual_files

def parse_options(argv):
    p = OptionParser(usage="usage: %prog [options] [input files]")
    p.add_option("-G", "--grl-path", type=str)
    p.add_option("-E", "--shell-on-exception", action="store_true")
    p.add_option("-L", "--limit", type=int, default=1000000000)
    p.add_option("-S", "--skip", type=int, default=0)
    p.add_option("-o", "--output", type=str, default="output.root")
    p.add_option("-s", "--obj-selection", type=str)
    p.add_option("--max-exception-count", type=int, default=10)
    
    options, args = p.parse_args(argv)
    files = args[1:]
    if not files:
        p.error("Specify files to run on!")
    
    actual_files = load_files(files)
    log.info("Operating on the following files:")
    log.info(pformat(actual_files[:10]))
    if len(actual_files) > 10:
        log.info("[skipped %i filenames]" % (len(actual_files) - 20))
        log.info(pformat(actual_files[-10:]))
        
    
    return options, make_chain(actual_files)
