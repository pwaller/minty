#! /usr/bin/env python

from minty import main
import sys

script, ana = sys.argv.pop(1), sys.argv.pop(1)
m = __import__(script, fromlist=[ana])
Analysis = getattr(m, ana)

main(Analysis)
