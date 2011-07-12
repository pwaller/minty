from textwrap import dedent
        
import re

from argparse import ArgumentParser
from yaml import YAMLObject, load, dump
import yaml

lumicalc_regex = re.compile(
    dedent(r"""
    .*?Beginning calculation for  Run (?P<run>\d+) LB \[(?P<since>\d+)\-(?P<until>\d+)\].*?
    .*?IntL recorded \((?P<unit>[munpf])b\^\-1\) : (?P<lumi>[0-9e\.\+]+)
    """).strip(), re.MULTILINE | re.DOTALL)
    
yaml.add_representer(tuple, 
    lambda dumper, value: dumper.represent_sequence(u'tag:yaml.org,2002:seq', value))

class LumiRun(YAMLObject):
    yaml_tag = u'!LumiCalc.Run'
    X_TO_MICRO = {"m" : 1e-3, "u" : 1e0, "n" : 1e3, "p" : 1e6, "f" : 1e9}
    
    def __init__(self):
        self.iovs = ()
          
    @classmethod
    def make_one(cls, since, until, unit, lumi):
        self = cls()
        lumi = float(lumi) * self.X_TO_MICRO[unit.lower()]
        self.iovs = (int(since), int(until), lumi),
        return self

    def __iadd__(self, rhs):
        self.iovs += rhs.iovs
        return self

    @property
    def total(self):
        return sum(lumi for since, until, lumi in self.iovs)

class LumiInfo(YAMLObject):
    yaml_tag = u'!LumiCalc.LumiInfo'
    
    def __init__(self, by_run=None):
        if by_run is None: by_run = {}
        self.by_run = by_run
    
    def __getitem__(self, run):
        run = int(run)
        if run not in self.by_run:
            self.by_run[run] = LumiRun()
        return self.by_run[run]
        
    def __setitem__(self, run, what):
        self.by_run[int(run)] = what
    
    @property
    def total_per_run(self):
        return dict((key, value.total) for key, value in self.by_run.iteritems())
    
    @classmethod
    def from_lumicalc(cls, filename):
        with open(filename) as fd:
            lumicalc = fd.read()
        self = cls()
        for run, since, until, unit, lumi in lumicalc_regex.findall(lumicalc):
            self[run] += LumiRun.make_one(since, until, unit, lumi)
        return self
    
    @classmethod
    def from_file(cls, filename):
        with open(filename) as fd:
            return load(fd)
        
    def to_file(self, filename):
        with open(filename, "w") as fd:
            fd.write(dump(self))    

def main():
    parser = ArgumentParser(description='Parse a lumicalc file')
    A = parser.add_argument
    A('-o', '--output-file', help="Output filename", default="lumi.yaml")
    A('input')
    
    args = parser.parse_args()
    
    from IPython.Shell import IPShellEmbed; ip = IPShellEmbed(["-pdb"])
    LumiInfo.from_lumicalc(args.input).to_file(args.output_file)
    
    
