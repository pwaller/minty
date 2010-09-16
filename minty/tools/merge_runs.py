#! /usr/bin/env python

# Scripts expect to be run with a cwd where "minty" and "pytuple" are present.
# (Or minty and pytuple are in the path)
import os; import sys; sys.path.insert(0, os.getcwd())

from minty.tools.hadd import merge_all

def main():
    with open("run_files") as fd:
        runs = [line.strip().split() for line in fd if line.strip()]
    
    for run in runs:
        run_no, files = run[0], run[1:]
        print "Merging run %s (%i files)" % (run_no, len(files))
        merge_all("mike-data-merged/%s.root" % run_no, files, 
                  selection="e.Run == %s" % run_no)
        
if __name__ == "__main__":
    main()
