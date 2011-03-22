#! /usr/bin/env python

from IPython.Shell import IPShellEmbed; ip = IPShellEmbed(["-pdb"])


from collections import namedtuple
from contextlib import contextmanager, closing
from cPickle import dumps, loads, UnpicklingError
from gc import collect, get_count, get_objects
from optparse import OptionParser
from os.path import exists
from shutil import rmtree
from tarfile import open as tarfile_open
from tempfile import mkdtemp
from time import time

import ROOT as R; R.kTRUE
from ROOT import gROOT, gSystem
from ROOT import TTree, TTreeCloner, kTRUE, kFALSE, TObjString

class UnableToMerge(Exception):
    """
    Raised when merging isn't possible
    """


## Copy Entries of a tree with the help of a TTreeCloner. Adapted from ROOT 5.28
def CopyEntries(to, tree, option=""):
    nbytes = 0
    treeEntries = tree.GetEntriesFast()
    nentries = treeEntries

    #// Quickly copy the basket without decompression and streaming.
    totbytes = to.GetTotBytes()
    i = 0
    while i < nentries:
        if tree.LoadTree(i) < 0:
            break;

            
        if to.GetDirectory():
            file2 = to.GetDirectory().GetFile()
            if file2 and (file2.GetEND() > TTree.GetMaxTreeSize()):
                if to.GetDirectory() == file2:
                    to.ChangeFile(file2);

        cloner = TTreeCloner(tree.GetTree(), to, option, TTreeCloner.kNoWarnings)
        if cloner.IsValid():
            to.SetEntries(to.GetEntries() + tree.GetTree().GetEntries())
            cloner.Exec()
        else:
            if i == 0:
              # If the first cloning does not work, something is really wrong
              # (since apriori the source and target are exactly the same structure!)
              raise Exception("Something is really wrong!")
            
            if cloner.NeedConversion():
                localtree = tree.GetTree()
                tentries = localtree.GetEntries()
                for ii in range(tentries):
                    if localtree.GetEntry(ii) <= 0:
                        break
                    to.Fill()
                if to.GetTreeIndex():
                    to.GetTreeIndex().Append(tree.GetTree().GetTreeIndex(), kTRUE)
            else:
                print("WARNING: %s" % str(cloner.GetWarning()))
                if tree.GetDirectory() and tree.GetDirectory().GetFile():
                    print("WARNING: Skipped file %s" % tree.GetDirectory().GetFile().GetName())
                else:
                    print("WARNING: Skipped file number %i" % tree.GetTreeNumber())
        # loop increment
        i += tree.GetTree().GetEntries()

    if to.GetTreeIndex():
        to.GetTreeIndex().Append(0, kFALSE); # Force the sorting

    nbytes = to.GetTotBytes() - totbytes
    return nbytes;

def tree_copy_selection(in_tree, out_tree, selection):
    """
    Copy `in_tree` to `out_tree`, checking selection(in_tree) for each event.
    """
    for entry in in_tree:
        if selection(entry):
            out_tree.Fill()
    
def tree_copy_duplicate_removal(in_tree, out_tree, key, keys):
    """
    Copy `in` to `out` for events where event.`key` does not exist in `keys`
    
    `keys` is the set of keys seen so far.
    TODO: Make it so that options.key can be an arbitrary expression like select?
    """
    for entry in in_tree:
        key_value = getattr(entry, key)
        if not key_value in keys:
            out_tree.Fill()
            keys.add(key_value)
# End of TTree copy utilities

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
    try:
        class_object = getattr(R, class_name)
        return class_object
    except AttributeError:
        return None
    
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

        if issubclass( type(self.merged_object), R.TFile ) and issubclass( type(next_object), R.TFile ):
            pass
        else: 
            assert_msg = "Attempt to merge incompatible types"
            assert type(self.merged_object) is type(next_object), assert_msg

        self.merge(next_object)
        
    def merge(self, next_object):
        raise NotImplementedError()
        
    def finish(self, key_name):
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

@define_merger(R.TObjString)
class PickledStringMerger(DefaultMerger):

    pyobject_merge_registry = {
        set: set.union,
        list: list.__add__,
        str: str.__add__,
        unicode: unicode.__add__,
    }
    
    def unpickle_string(self, string):
        try:
            return loads(string.GetName())
        except UnpicklingError:
            raise UnableToMerge

    def __init__(self, first_object, target_directory):
        self.merged_object = self.unpickle_string(first_object)
        t = type(self.merged_object)
        self.merger_function = self.pyobject_merge_registry.get(t)
        if not self.merger_function:
            raise RuntimeError("I don't know how to merge objects of type %r" % t)
        
    def merge(self, next_object):
        do_merge = self.merger_function
        try:
            next_object = self.unpickle_string(next_object)
        except UnpicklingError:
            # Silently ignore non-python strings
            return
        self.merged_object = do_merge(self.merged_object, next_object)
        #UnpicklingError
        #new_value = self.merged_object.GetVal() + next_object.GetVal()
        #self.merged_object.SetVal(new_value)


    def finish(self, key_name):
        self.merged_object = TObjString(dumps(self.merged_object))
        self.merged_object.Write(key_name)
        #super(PickledStringMerger, self).finish()

@define_merger(R.TTree)
class TreeMerger(DefaultMerger):
    key = None
    selection = None
    def __init__(self, first_object, target_directory):
        with root_directory(target_directory):
            self.merged_object = first_object.CloneTree(0)
            self.merge(first_object)

    def merge(self, in_tree):
        # Updated in tree_copy_duplicate_removal
        keys = set()
        out_tree = self.merged_object

        in_tree.CopyAddresses(out_tree)
        if TreeMerger.key:
            tree_copy_duplicate_removal(in_tree, out_tree, TreeMerger.key, keys)
        elif TreeMerger.selection:
            expr = eval(compile("lambda e: %s" % TreeMerger.selection,
                       "<command line --select option>", "eval"))

            tree_copy_selection(in_tree, out_tree, expr)
        else:
            CopyEntries(out_tree, in_tree)

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
            try:
                if merger:
                    merger.merge(key.ReadObj())
            except UnableToMerge:
                pass
            return 
            
        KeyClass = get_key_class(key)
        
        if KeyClass and issubclass(KeyClass, R.TDirectory):
            # Create the target subdirectory and run the merge
            original_directory = key.ReadObj()
            with root_directory(self.merged_object):
                new_target_directory = self.merged_object.mkdir(name)            
                merger = DirectoryMerger(original_directory, new_target_directory)
        else:
            MergerClass = getattr(KeyClass, "_py_merger", None)
            merger = None
            try:
                if MergerClass:
                    merger = MergerClass(key.ReadObj(), self.merged_object)
            except UnableToMerge:
                # Silently ignore objects we can't merge
                pass
            
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
    
    def finish(self, key_name=None):
        with root_directory(self.merged_object):
            for this_key_name, merger in sorted(self.contents.iteritems()):
                if not merger:
                    # An unsupported class.
                    continue
                merger.finish(this_key_name)

def try_tarfile(filename, pattern):
    with closing(tarfile_open(filename)) as tar:
        for f in tar.getmembers():
            if ".root" in f.path and (not pattern or pattern in f.path):
                print " -", f.path
                tmpdir = mkdtemp()
                tar.extract(f.path, tmpdir)
                yield R.TFile(tmpdir + "/" + f.path)
                rmtree(tmpdir)

def root_file_generator(filenames, pattern, fs=False, fs_protocol='rfio'):
    for i, filename in enumerate(filenames):
        print "Complete:", i, "/", len(filenames), filename
        with timer("process file %i" % i):
            if fs:
                yield TCopyFile(filename)
            elif ".tgz" in filename:
                for f in try_tarfile(filename, pattern):
                    yield f
            else:
                yield R.TFile.Open(filename)
def init_file_stager(fs_protocol='rfio'):

    ## Try to load FileStager library
    print 'Loading FileStager library ...'
    gSystem.Load('libFileStagerLib')
    from ROOT import TStageManager, TCopyFile, TCopyChain
    gROOT.GetPluginManager().AddHandler("TFile", "^gridcopy:", "TCopyFile","TCopyFile_cxx", "TCopyFile(const char*,Option_t*,const char*,Int_t)")

    print 'Enabling FileStager ...'
    TCopyChain.SetOriginalTChain(False)
    TCopyFile.SetOriginalTFile(False)

    print 'Setting up FileStager manager ...'
    mgr = TStageManager.instance()
    mgr.setInfilePrefix('gridcopy://')
    mgr.setOutfilePrefix('file:')
    mgr.setCpCommand('%s/fs_copy' % this_directory )
    mgr.addCpArg('-v')
    mgr.addCpArg('--vo')
    mgr.addCpArg('atlas')
    mgr.addCpArg('-t')
    mgr.addCpArg('1200')
    mgr.addCpArg('-p')
    mgr.addCpArg(fs_protocol)
    mgr.verbose()
    mgr.verboseWait()
   
    return mgr, TCopyFile

def merge_files(output_filename, input_filenames, pattern=None, fs=False, fs_protocol='rfio'):

    output_file = R.TFile(output_filename, "recreate")
    output_file.SaveSelf(True)
    
    input_generator = root_file_generator(input_filenames, pattern, fs, fs_protocol)
    try:
        first_file = input_generator.next()
    except StopIteration:
        print "No files to merge!"
        return 1
    
    directory_merger = DirectoryMerger(first_file, output_file)
    
    try:
        for input_file in input_generator:
            directory_merger.merge(input_file)
    finally:
        directory_merger.finish()
    
    return 0

def main():
    parser = OptionParser()
    parser.add_option("-o", "--outfile", default="merged.root",
                      help="output file")
    parser.add_option("-f", "--force", action="store_true",
                      help="overwrite output file if it exists. (default: no)")
    parser.add_option("-k", "--key", default=None,
                      help="use this key for making any trees unique (default: None)")
    parser.add_option("-s", "--select", default=None, dest="selection",
                      help="a python string which is evaluated with 'e' as the "
                           "event, used to choose whether a given event will "
                           "be copied.")
    parser.add_option("-t", "--stager", action="store_true", dest="fs",
                      help="enables the file stager for reading input files.")
    parser.add_option("-p", "--protocol", default="rfio", dest="fs_protocol",
                      help="sets copy protocol for file stager.")
                      
    parser.add_option("-P", "--pattern",
                      help="Only merge files which contain this string (matches"
                           " filenames inside tarfiles if processing tar files)")

    from sys import argv
    options, input_filenames = parser.parse_args(argv)
    input_filenames = input_filenames[1:]

    if not input_filenames:
        parser.print_help()
        parser.error("Please specify a list of files to be merged")

    if options.fs and options.fs_protocol.lower() not in ['lcgcp','rfio','gsidcap','dcap','gsiftp','file']:
        parser.print_help()
        parser.error("file stager protocole %s not supported" % options.fs_protocol)

    if options.fs and not file_stager_available:
        parser.error("file stager library could not be loaded!")
    
    TreeMerger.key = options.key
    TreeMerger.selection = options.selection
    output_name = options.outfile
    if exists(output_name) and not options.force:
        raise RuntimeError("'%s' already exists. Use --force to overwrite"
                           % (output_name))
                           
    return merge_files(output_name, input_filenames, options.pattern, 
                       fs=options.fs, fs_protocol=options.fs_protocol)

if __name__ == "__main__":
    main()
