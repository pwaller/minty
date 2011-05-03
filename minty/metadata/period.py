#! /usr/bin/env python

from os import listdir
from os.path import join as pjoin
from pkg_resources import resource_string, get_provider
from yaml import dump, load

import re
import sys

PERIODS_DIRECTORY = "/afs/cern.ch/atlas/www/GROUPS/DATAPREPARATION/DataPeriods/"

# run to period mapping
RUN_TO_PERIOD = load(resource_string(__name__, "periods.yaml"))

def period_from_run(run):
    for period, (first, last) in RUN_TO_PERIOD.items():
        if first <= run <= last:
            return period, (first, last)
    return "UNK", (run, run)
    #assert False, "Outside known period: %i" % run

def generate_mapping():
    ds = re.compile(r'data(\d{2})_\d+TeV\.period([A-Z][0-9]+)\.runs\.list$')
    mapping = {}
    for f in [pjoin(PERIODS_DIRECTORY, f) for f in listdir(PERIODS_DIRECTORY)]:
        match = ds.search(f)
        if not match:
            continue
        year, period = match.groups()
    
        with open(f) as fd:
            runs = map(int, [l for l in fd.readlines() if l])
            first, last = min(runs), max(runs)
            mapping["%s_%s" % (year, period)] = (first, last)
            
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
