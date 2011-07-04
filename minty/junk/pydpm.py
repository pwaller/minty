#! /usr/bin/env python

LIVERPOOL_DPM = "/dpm/ph.liv.ac.uk/home/atlas/atlasliverpooldisk"

import re

from ctypes import (CDLL, POINTER, Structure, pointer, c_int, c_char_p, c_char, 
                    c_uint8, c_short, c_ushort, c_long, c_void_p, c_uint64)


from fnmatch import translate
from threading import Thread
from Queue import Queue
from stat import S_ISDIR
from os.path import join as pjoin
    
from platform import architecture
# Needs changing for 64 bit
c_time_t = c_long
assert architecture() == ("32bit", "ELF"), (
    "c_time_t needs changing for non-32 bit platforms")
    
# Seems to be optimal. More doesn't give a speedup.
N_THREADS = 15 #5

class c_dpns_DIR_p(c_void_p): pass
    
class c_dpns_direnstat(Structure):
    _fields_ = [
        ("fileid", c_uint64), ("mode", c_int), ("nlink", c_int), 
        ("uid", c_long), ("gid", c_long), ("filesize", c_uint64),
        ("atime", c_time_t), ("mtime", c_time_t), ("ctime", c_time_t),
        ("fileclass", c_short), ("status", c_char), ("reclen", c_ushort),
        ("d_name", c_char*1024),
    ]
    
c_dpns_direnstat_p = POINTER(c_dpns_direnstat)

def make_fn(what, res, *args):
    what.restype = res
    what.argtypes = args
    return what

libdpm = CDLL("libdpm.so")
dpns_opendir  = make_fn(libdpm.dpns_opendir,  c_dpns_DIR_p,       c_char_p)
dpns_readdirx = make_fn(libdpm.dpns_readdirx, c_dpns_direnstat_p, c_dpns_DIR_p)
dpns_closedir = make_fn(libdpm.dpns_closedir, c_int,              c_dpns_DIR_p)

def get_file_list(dirname):
    """
    Equivalent to dpns-ls, yields a list of files/directories with their size.
    """
    dpns_dir = dpns_opendir(dirname)
    assert dpns_dir, "Directory '%s' not found" % dirname
    
    try:
        while True:
            dirent = dpns_readdirx(dpns_dir)
            if not dirent: break
            dirent = dirent.contents
            yield dirent.d_name, dirent.mode, dirent.filesize
            
    finally:
        dpns_closedir(dpns_dir)

class ParallelFileListGetter(Thread):
    """
    A worker thread which reads from `inputQ` and appends to `output`
    """
    def __init__ (self, inputQ, output):
        Thread.__init__(self)
        self.inputQ, self.output = inputQ, output
        self.setDaemon(True)
        self.start()

    def run(self):
        while True:
            dirname = self.inputQ.get()
            self.inputQ.task_done()
            if dirname is None: break
            self.output.append((dirname, list(get_file_list(dirname))))

def parallel_get_file_list(dirname, dirs):
    """
    Executes get_file_list in parallel on `dirs`
    """
    inQ, output = Queue(), []
    for path in dirs:
        inQ.put("/".join((dirname, path)))
    
    # Create at most five threads which each query directories.
    for i in xrange(min(N_THREADS, len(dirs))):
        t = ParallelFileListGetter(inQ, output)
        inQ.put(None)
    
    inQ.join()
    
    return output
        
def walk(dirname, file_list=None, with_size=False, depth=0, with_depth=False):
    """
    Mimicks os.walk, but works for DPM.
    """
    
    if file_list is None:
        file_list = get_file_list(dirname)
    
    files, dirs = [], []
    for path, mode, filesize in file_list:
        if S_ISDIR(mode):
            dirs.append(path)
        else:
            files.append((path, filesize) if with_size else path)
    
    if with_depth:
        yield dirname, dirs, files, depth
    else:
        yield dirname, dirs, files
    
    for path, file_list in sorted(parallel_get_file_list(dirname, dirs)):
        for entry in walk(path, file_list, with_size, depth+1, with_depth):
            yield entry

def test(input_path):
    
    base = input_path.count("/")
    
    def wanted(dirname):
        return dirname.startswith("data09") and "L1CaloEM" in dirname
    
    paths = []
    
    for path, dirs, files in walk(input_path, with_size=True):
        depth = path.count("/")-base
        
        dirs[:] = filter(wanted, dirs)
        #print " "*depth, path, len(dirs), len(files)
        for filename, filesize in files:
            paths.append("/".join((path, filename)))
            #print " "*depth, "", filename
    
    print "%i files matched" % len(paths)

def glob_dpm(glob_string):
    
    path_elements = glob_string.split("/")
    
    glob_pieces = map(lambda s: "*" in s, path_elements)
    depth = (glob_pieces.index(True) 
             if True in glob_pieces else len(path_elements))
        
    this_pathbit = "/".join(path_elements[:depth]) # A directory we can dpns-ls
    result = []
    
    for path, dirs, files, depth in walk(this_pathbit, depth=depth,
                                         with_depth=True, with_size=True):
        
        if depth >= len(path_elements):
            # Too deep!
            continue

        expr = re.compile(translate(path_elements[depth]))       
        
        # Keep only paths which match 
        dirs[:] = [x for x in dirs if expr.match(x)] # [:] -> replace "in place"
        
        if depth == len(path_elements)-1:
            # We're the right depth to match files
            files = [(pjoin(path, f), s) for f, s in files if expr.match(f)]
            result.extend(files)
    
    if not result: return [], 0
    
    files, sizes = zip(*result)
    return files, sum(sizes)

def glob_liv_dpm(glob_string):
    return glob_dpm(pjoin(LIVERPOOL_DPM, glob_string))

def main(argv):
    argv = argv[1:]
    if not argv:
        input_path = "*/*"
    else:
        input_path = argv[0]
    
    filenames, size = glob_liv_dpm(input_path)
    
    for filename in filenames:
        print filename
        
    print "Found %i matches in %.3f GB" % (len(filenames), size / 1024**3.)

if __name__ == "__main__":
    from sys import argv
    main(argv)
