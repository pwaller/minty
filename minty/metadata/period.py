#! /usr/bin/env python

from os import listdir
from os.path import join as pjoin
from pkg_resources import resource_string, get_provider
from yaml import safe_dump, load

import re
import sys

# run to period mapping
RUN_TO_PERIOD = None

def load_period_mapping():
    global RUN_TO_PERIOD
    if not RUN_TO_PERIOD:
        period_runs = load(resource_string(__name__, "periods.yaml"))
        RUN_TO_PERIOD = {}
        for period, runs in sorted(period_runs.iteritems()):
            for run in runs:
                RUN_TO_PERIOD[run] = period
    return RUN_TO_PERIOD

def period_from_run(run):
    if run < 152166:
        return "MC"    
    return load_period_mapping().get(run, "UNK")

def generate_mapping():
    from DQUtils.periods import fetch_project_period_runs

    mapping = {}
    
    for project, period_runs in sorted(fetch_project_period_runs().iteritems()):
        for period, runs in sorted(period_runs.iteritems()):
            if period == "AllYear" or "VdM" in period:
                continue
            if not period[-1].isdigit():
                continue
            mapping["{0}_{1}".format(project, period)] = runs
            
    return mapping

def update_periods_file():
    mapping = generate_mapping()
    
    path = get_provider(__name__).module_path
    with open(pjoin(path, "periods.yaml"), "wb") as fd:
        fd.write(safe_dump(mapping))
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
