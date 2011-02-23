#! /usr/bin/env python

from tarfile import open as open_tarfile
from contextlib import closing

from pprint import pprint

EXEC_LINE = "=== execute ==="
LS_LINE = "=== ls . ==="

def extract_regions(items, firstpart, secondpart, cutoff=None):
    item_iter = iter(items)
    while True:
        for item in item_iter:
            if firstpart(item):
                yield item
                break
        else:
            break
            
        for i, item in enumerate(item_iter):
            if secondpart(item) or (cutoff and i > cutoff):
                if firstpart(item):
                    yield item
                break
            yield item
        else:
            break

def extract_error(log_contents):
    lines = extract_regions(log_contents.split("\n"), 
                            lambda line: "ERROR" in line,
                            lambda line: line.startswith("["))
    return "\n".join(lines)

def process_file(path, tar):
    for fileinfo in tar.getmembers():
        if not fileinfo.isfile() or fileinfo.isdir():
            continue
        filename = fileinfo.name
        if not (filename.endswith("_stderr.txt") or filename.endswith("_stdout.txt")):
            continue
        
        with closing(tar.extractfile(fileinfo)) as tarfile_fd:
            contents = tarfile_fd.read()
            if not contents:
                continue
            contents = contents[contents.index(EXEC_LINE)+len(EXEC_LINE)+1:]
            contents = contents[:contents.index(LS_LINE)]
        
        if "ERROR" in contents:
            print path
            print extract_error(contents)

def main():
    from optparse import OptionParser
    o = OptionParser()
    options, args = o.parse_args()
    main(args)

    for path in args:
        with closing(open_tarfile(path)) as tar:
            process_file(path, tar)

if __name__ == "__main__":
    main()
