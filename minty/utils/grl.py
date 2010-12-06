#! /usr/bin/env python

import xml.etree.cElementTree as cElementTree

from collections import defaultdict
from os import listdir
from os.path import join as pjoin
from os.path import isfile

class FakeGRL(object):
    def __contains__(self, (run, lb)):
        return True

class GRL(object):
    def __init__(self, grldir):
        self.grl = defaultdict(set)
        if isfile(grldir):
            self.parse_xml(grldir)
            return
        for filename in listdir(grldir):
            if filename.endswith(".xml"):
                self.parse_xml(pjoin(grldir, filename))
            
    def __contains__(self, (run, lb)):
        return lb in self.grl[run]
        
    def parse_xml(self, xml_file):
        xml = cElementTree.parse(xml_file)

        for lbc in xml.getiterator('LumiBlockCollection'):
            run = int(lbc.find('Run').text)
            for lbr in lbc.findall('LBRange'):
                runs = xrange(int(lbr.get('Start')), int(lbr.get('End')) + 1)
                self.grl[run].update(runs)
