#! /usr/bin/env python

from IPython.Shell import IPShellEmbed; ip = IPShellEmbed(["-pdb"])

from collections import namedtuple
from contextlib import contextmanager
from gc import collect, get_count, get_objects
from itertools import chain
from optparse import OptionParser
from os import walk
from os.path import exists, join as pjoin
from pprint import pprint
from time import time

import ROOT as R; R.kTRUE


class define_merger(object):
    def __init__(self, *classes):
        self.merger_classes = classes
        
    def __call__(self, function):
        for merger_class in self.merger_classes:
            merger_class._py_merger = staticmethod(function)
        return function


DirectoryContentItem = namedtuple("DirectoryContentItem", "type obj")

def alive_objects():
    return len(get_objects())

@contextmanager
def timer(what):
    start = time()
    alive_before = alive_objects()
    try: yield
    finally:
        alive_after = alive_objects()
        #print "Took %.2f to %s" % (time()-start, what), 
        #print "(alive objects: pre: %i post: %i)" % (alive_before, alive_after)

@contextmanager
def root_directory(directory):
    previous_dir = R.gDirectory.GetDirectory("")
    try:
        directory.cd()
        yield
    finally:
        previous_dir.cd()

def get_key_class(key):
    class_name = key.GetClassName()
    class_object = getattr(R, class_name)
    return class_object
    
def most_recent_cycle_keys(directory):
    """
    Returns a list of all the keys in a directory, only taking the most recent
    TKey.GetCycle() per TKey.GetName().
    
    Strategy: maintain a dictionary of key names, where the value is the largest
    (cycle_number, key_object) seen, which is the largest cycle_number seen.
    """
    most_recent = {}
    # Generate a list of (name, (cyclenum, keyobject)) values
    all_keys = list(directory.GetListOfKeys())
    keys = ((k.GetName(), (k.GetCycle(), k)) for k in all_keys)
    for name, cyclekey in keys:
        most_recent[name] = (max(cyclekey, most_recent[name]) 
                             if name in most_recent else cyclekey)
                             
    # Just the key objects, sorted in name order.
    recent_keys = [key for name, (cycle, key) in sorted(most_recent.iteritems())]
    
    # Return all_keys so that we don't lose anything
    return all_keys, recent_keys
        
def get_path(directory):
    filename, path = directory.GetPath().split(":")
    return filename, path


class DefaultMerger(object):
    def __init__(self, first_object, target_directory):
        with root_directory(target_directory):
            self.merged_object = first_object
            #first_object.Clone()
        #self.merged_object.SetBit(R.TObject.kCanDelete, False)
        #R.SetOwnership(self.merged_object, True)
        #target_directory.Append(self.merged_object)
    
    def merge_safe(self, next_object):
        # Note not using isinstance here because we don't want to allow merging
        # subclasses
        assert_msg = "Attempt to merge incompatible types"
        assert type(self.merged_object) is type(next_object), assert_msg
        self.merge(next_object)
        
    def merge(self, next_object):
        raise NotImplementedError()
        
    def finish(self):
        self.merged_object.Write()


class HasSetDirectory(object):
    """
    Indicates that the `first_object` needs to be disconnected from the input
    with SetDirectory(None)
    """
    def __init__(self, first_object, target_directory):
        super(HasSetDirectory, self).__init__(first_object, target_directory)
        first_object.SetDirectory(None)
        

@define_merger(R.THnSparse)
class HistogramMerger(DefaultMerger):
    def merge(self, next_object):
        self.merged_object.Add(next_object)
        
        
@define_merger(R.TH1)
class THMerger(HasSetDirectory, HistogramMerger):
    "Merges things deriving from TH1. Note dependence on HasSetDirectory"


@define_merger(*(
    getattr(R, "TParameter<%s>" % cpp_type)
    for cpp_type in ("int", "long", "Long64_t", "float", "double")
))
class ParameterMerger(DefaultMerger):
    def merge(self, next_object):
        new_value = self.merged_object.GetVal() + next_object.GetVal()
        self.merged_object.SetVal(new_value)


@define_merger(R.TDirectory)
class DirectoryMerger(DefaultMerger):
    """
    The DirectoryMerger will merge all objects within a directory, recursively
    merging subdirectories.
    """
    def __init__(self, first_object, target_directory):
        self.contents = {}
        self.merged_object = target_directory
        with timer("Clear"):
            first_object.Clear()
        with timer("Do merge"):
            self.merge_safe(first_object)

    def merge_one_key(self, key):
        name = key.GetName()
        if name in self.contents:
            # We already know how to deal with this key
            merger = self.contents[name]
            if merger:
                merger.merge(key.ReadObj())
            return 
            
        KeyClass = get_key_class(key)
        
        if issubclass(KeyClass, R.TDirectory):
            # Create the target subdirectory and run the merge
            original_directory = key.ReadObj()
            with root_directory(self.merged_object):
                new_target_directory = self.merged_object.mkdir(name)            
                merger = DirectoryMerger(original_directory, new_target_directory)
        else:
            MergerClass = getattr(KeyClass, "_py_merger", None)
            if MergerClass:
                merger = MergerClass(key.ReadObj(), self.merged_object)
            else:
                # TODO: Record classes we're incapable of merging
                self.contents[name] = None
                return
            
        self.contents[name] = merger
    
    def merge(self, next_object):
        with timer("Fetch most recent keys"):
            all_keys, new_keys = most_recent_cycle_keys(next_object)
        
        #print "  Total objects in merge registry:", len(self.contents)
        #print "  Number of keys: %5i, %5i" % (len(all_keys), len(new_keys))
        
        with timer("iterate over keys"):
            for key in new_keys:
                self.merge_one_key(key)
        
        with timer("Close file and collect"):
            next_object.Close()
            
            # This would happen anyway, but is here as a reminder that it needs
            # to happen AFTER we close the directory from which the keys came. 
            del all_keys
            del new_keys
            collect()
    
    def finish(self):
        with root_directory(self.merged_object):
            for keyname, merger in sorted(self.contents.iteritems()):
                if not merger:
                    # An unsupported class.
                    continue
                merger.finish()

def root_file_generator(filenames):
    for i, filename in enumerate(filenames):
        print "Complete:", i, "/", len(filenames), filename
        with timer("process file %i" % i):
            yield R.TFile(filename)

def merge_files(output_filename, input_filenames):
    output_file = R.TFile(output_filename, "recreate")
    output_file.SaveSelf(True)
    
    input_generator = root_file_generator(input_filenames)
    first_file = input_generator.next()
    
    directory_merger = DirectoryMerger(first_file, output_file)
    
    try:
        for input_file in input_generator:
            directory_merger.merge(input_file)
    finally:
        directory_merger.finish()

def main():

    parser = OptionParser()
    parser.add_option("-o", "--outfile", default="merged.root",
                      help="output file")
    parser.add_option("-f", "--force", action="store_true",
                      help="overwrite output file if it exists. (default: no)")

    from sys import argv
    options, input_filenames = parser.parse_args(argv)
    input_filenames = input_filenames[1:]

    if not input_filenames:
        parser.print_help()
        parser.error("Please specify a list of files to be merged")
    
    output_name = options.outfile
    if exists(output_name) and not options.force:
        raise RuntimeError("'%s' already exists. Use --force to overwrite"
                           % (output_name))
                           
    merge_files(output_name, input_filenames)
