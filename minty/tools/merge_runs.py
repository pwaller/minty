#! /usr/bin/env python

# Scripts expect to be run with a cwd where "minty" and "pytuple" are present.
# (Or minty and pytuple are in the path)
import os; import sys; sys.path.insert(0, os.getcwd())

from minty.tools.hadd import merge_all

MERGE_LIST, INPUT_PATH = "run_files", "mike-data-merged"
MERGE_LIST, INPUT_PATH = "mike_runs_2_skim", "mike-data-merged-2"

def main():
    with open(MERGE_LIST) as fd:
        runs = [line.strip().split() for line in fd if line.strip()]
    
    for run in runs:
        run_no, files = run[0], run[1:]
        print "Merging run %s (%i files)" % (run_no, len(files))
        merge_all(INPUT_PATH + "/%s.root" % run_no, files, 
                  selection="e.Run == %s" % run_no)
        
if __name__ == "__main__":
    main()
