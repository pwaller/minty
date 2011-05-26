#! /usr/bin/env python

from os import listdir
from os.path import join as pjoin
from pkg_resources import resource_string, get_provider
from yaml import dump, load

import re
import sys

# run to period mapping
RUN_TO_PERIOD = load(resource_string(__name__, "periods.yaml"))

def period_from_run(run):
    for period, (first, last) in RUN_TO_PERIOD.items():
        if first <= run <= last:
            return period, (first, last)
    return "UNK", (run, run)
    #assert False, "Outside known period: %i" % run

def generate_mapping():
    from DQUtils.periods import fetch_project_period_runs

    mapping = {}
    
    for project, period_runs in sorted(fetch_project_period_runs().iteritems()):
        for period, runs in sorted(period_runs.iteritems()):
            if period == "AllYear" or "VdM" in period:
                continue
            if not period[-1].isdigit():
                continue
            mapping["{0}_{1}".format(project, period)] = min(runs), max(runs)
            
    return mapping

def update_periods_file():
    mapping = generate_mapping()
    
    path = get_provider(__name__).module_path
    with open(pjoin(path, "periods.yaml"), "wb") as fd:
        fd.write(dump(mapping))
    print "Periods file updated with %i entries" % len(mapping)

def check_mapping():
    mapping = generate_mapping()
    if mapping != RUN_TO_PERIOD:
        print "Run-Period mapping is out of date"
        return 1
    return 0

def main():
    if "-c" in sys.argv:
        raise SystemExit(check_mapping())
    update_periods_file()

if __name__ == "__main__":
    main()
