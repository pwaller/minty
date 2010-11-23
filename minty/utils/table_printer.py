#coding: UTF8
"""
Prints out a table, padded to make it pretty.

call pprint_table with an output (e.g. sys.stdout, cStringIO, file)
and table as a list of lists. Make sure table is "rectangular" -- each
row has the same number of columns.

MIT License

Taken from:
http://ginstrom.com/scribbles/2007/09/04/pretty-printing-a-table-in-python/

Found with the google search "python print table" March 2010

Minor modifications by <peter.waller@cern.ch> to include a "-" seperator for
the header, and to change the number format code.

"""

__version__ = "0.1"
__author__ = "Ryan Ginstrom"

import sys

def comma_num(x):
    if x < 0: return "-" + comma_num(-x)
    parts = []
    while x >= 1000:
        x, r = divmod(x, 1000)
        if r % 1:
            parts.append("%06.2f" % r)
        else:
            parts.append("%03i" % r)
    
    front = "%3f" % x if x % 1 else str(int(x))
    return ",".join(([front] if x or not parts else []) + list(reversed(parts)))

def format_num(num):
    """Format a number according to given places.
    Adds commas, etc."""
    if isinstance(num, (int, long, float)):
        return comma_num(num)
        
    return str(num)

def get_max_width(table, index):
    """Get the maximum width of the given column index
    """
    
    return max([len(format_num(row[index])) for row in table])

def pprint_table_to(out, table, header_loc=1):
    """Prints out a table of data, padded for alignment
    
    @param out: Output stream ("file-like object")
    @param table: The table to print. A list of lists. Each row must have the same
    number of columns.
    
    """

    col_paddings = []
    
    for i in range(len(table[0])):
        col_paddings.append(get_max_width(table, i))

    for i, row in enumerate(table):
        if i == header_loc:
            print >> out, "-" * (sum(col_paddings) + (len(col_paddings)*3-1))
        # left col
        print >> out, row[0].ljust(col_paddings[0] + 2),
        # rest of the cols
        for i in range(1, len(row)):
            col = format_num(row[i]).rjust(col_paddings[i] + 2)
            print >> out, col,
        print >> out

def pprint_table(table, header_loc=1):
    pprint_table_to(sys.stdout, table, header_loc)

def pprint_table_string(table, header_loc=1):
    from cStringIO import StringIO
    sio = StringIO()
    pprint_table_to(sio, table, header_loc)
    return sio.getvalue()
    
if __name__ == "__main__":
    table = [["", "taste", "land speed", "life"],
        ["spam", 300101, 4, 1003],
        ["eggs", 105, 13, 42],
        ["lumberjacks", 13, 105, 10]]
    
    pprint_table(table)
