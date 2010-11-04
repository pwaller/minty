#! /usr/bin/env python
"""
Outputs a list of filenames which contain each run
"""

# Scripts expect to be run with a cwd where "minty" and "pytuple" are present.
# (Or minty and pytuple are in the path)
import os; import sys; sys.path.insert(0, os.getcwd())

from minty import main, AnalysisBase
from logging import getLogger; log = getLogger("minty.tools.discover_run_files")

def record_run(ana, event):
    """
    Record a list of {runnumber : [filenames]}
    """
    this_tree, this_run = event.tree.GetTree(), event.RunNumber
    if ana.last_tree != this_tree or ana.last_run != this_run:
        ana.last_tree, ana.last_run = this_tree, this_run
        this_file = this_tree.GetDirectory().GetName()
        ana.runs.setdefault(this_run, []).append(this_file)

class RunDiscoverer(AnalysisBase):
    def __init__(self, tree, options):    
        super(RunDiscoverer, self).__init__(tree, options)
        
        self.last_tree = self.last_run = None
        self.runs = {}
        
        self.tasks.extend([
            record_run,
        ])

    def finalize(self):
        log.info("Completed")
        for run, files in sorted(self.runs.iteritems()):
            print run, " ".join(sorted(files))

if __name__ == "__main__":
    main(RunDiscoverer)
