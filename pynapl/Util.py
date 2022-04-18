# Utility functions

from functools import reduce
import operator


def product(seq):
    """The product of a sequence of numbers"""
    return reduce(operator.__mul__, seq, 1) 

def scan_reverse(f, arr):
    """Scan over a list in reverse, using a function"""
    r=list(arr)
    for i in reversed(range(len(r))[1:]):
        r[i-1] = f(r[i-1],r[i])
    return r

def extend(arr,length):
    """Extend a list APL-style"""
    if len(arr) >= length: return arr[:length]
    else:
        r=arr[:]
        while length-len(r) >= len(arr):
            r.extend(arr)
        else:
            r.extend(arr[:length-len(r)])
        return r

