# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import sys
import operator
import json
import codecs
import collections

from .Util import *

# in Python 3, the distinction between "long" and "int" doesn't exist
# anymore
if sys.version_info.major >= 3:
    long = int 

# define (str, bytes) to be their Python 3 types
if sys.version_info.major == 2:
    bytes = str
    str = unicode

# assuming ⎕IO=0 for now
class APLNamespace(object):
    def __init__(self, dct=None):
        if dct is None: self.dct={}
        else: self.dct=dct

    def __getitem__(self, x):
        return self.dct[x]

    def __setitem__(self, x, val):
        self.dct[x] = APLArray.from_python(val, enclose=False)

    def toJSONString(self):
        return json.dumps(self, cls=ArrayEncoder, ensure_ascii=False)

    # convert an APL namespace to a Python dictionary
    def to_python(self):
        newdct = {}
        for x in self.dct:
            obj = self.dct[x]
            if isinstance(obj, APLArray) \
            or isinstance(obj, APLNamespace):
                newdct[x] = obj.to_python()
            else:
                newdct[x] = obj
        return newdct

    @staticmethod
    # convert a Python dictionary to an APL namespace
    def from_python(dct):
        newdct = {}
        for x in dct: 
            newdct[x] = APLArray.from_python(dct[x])
        return APLNamespace(newdct)


    @staticmethod 
    def fromJSONString(string):
        return APLArray._json_decoder.decode(string)



class APLArray(object):
    """Serializable multidimensional array.
      
    Every element of the array must be either a value or another array. 
    """
    
    TYPE_HINT_NUM = 0
    TYPE_HINT_CHAR = 1

    data=None
    rho=None
    type_hint=None

    # json decoder object hook
    def __json_object_hook(jsobj):
        # if this is an APL array, return it as such
        
        if type(jsobj) is dict:
            if 'r' in jsobj and 'd' in jsobj:
                # this is an APL array
                type_hint = APLArray.TYPE_HINT_NUM
                if 't' in jsobj: type_hint = jsobj['t']
                return APLArray(jsobj['r'], list(jsobj['d']), type_hint=type_hint)
            elif 'ns' in jsobj:
                # this is an APL namespace, which can be represented as a dict in Python
                return APLNamespace(jsobj['ns'])
            elif 'imag' in jsobj:
                # this is a complex number
                return complex(jsobj['real'], jsobj['imag'])
            else:
                return jsobj
        else:
            return jsobj
    
    # define a reusable json decoder
    _json_decoder = json.JSONDecoder(object_hook=__json_object_hook)


    # convert array to suitable-ish python representation
    def to_python(self):
        """Convert an APLArray to a Python object.

        Multidimensional arrays will be split up row-by-row and returned as a nested list, 
        as if one had done ↓."""

        if len(self.rho)==0: # scalar
            scalar = self.data[0]
            if isinstance(scalar, APLArray): return scalar.to_python()
            elif isinstance(scalar, APLNamespace): return scalar.to_python()
            else: return scalar

        elif len(self.rho)==1: # array
            # if the type hint says characters, and the array is simple, return a string
            if self.genTypeHint() == APLArray.TYPE_HINT_CHAR \
            and not any(isinstance(x, APLArray) or isinstance(x, APLNamespace) for x in self.data):
                return ''.join(self.data)

            # if not, return a list. If this is a nested array that _does_ have a simple
            # string in it somewhere, *that* string *will* show up as a string within the
            # converted object
            else:
                pylist = []
                for item in self.data:
                    if isinstance(item,APLArray) or isinstance(item,APLNamespace): 
                        item=item.to_python()
                    
                    pylist.append(item)
                return pylist

        elif len(self.rho)>=2: # higher-rank array
            # split the array until it is entirely flat
            arr = self
            # nocopy is safe here because arr is never modified
            while len(arr.rho)>0: arr=arr.split(nocopy=True)
            # convert the flattened array to a python representation
            return arr.to_python()

        raise RuntimeError("rho < 0; rho=%d!" % self.rho)


    @staticmethod
    def from_python(obj, enclose=True):
        """Create an APLArray from a Python object.
        
        Objects may be numbers, strings, or lists.

        If the object is already an APLArray, it will be returned unchanged.
        """
    
        if obj is None:
            return APLArray.from_python([]) #Return the empty list for "None"

        if isinstance(obj, APLArray) \
        or isinstance(obj, APLNamespace):
            return obj # it already is of the right type

        if type(obj) is dict:
            # convert all items in the dictionary to APL representation
            return APLNamespace.from_python(obj)

        # lists, tuples and strings can be represented as vectors
        if type(obj) in (list,tuple):
            return APLArray(rho=[len(obj)], 
                            data=[APLArray.from_python(x,enclose=False) for x in obj])
        
        # numbers can be represented as numbers, enclosed if at the upper level so we always send an 'array'
        elif type(obj) in (int,long,float,complex): 
            if enclose: return APLArray(rho=[], data=[obj], type_hint=APLArray.TYPE_HINT_NUM)
            else: return obj

        # boolean scalars should convert to ints for APL's sake
        elif type(obj) is bool:
            return APLArray.from_python(int(obj))

        # a one-element string is a character, a multi-element string is a vector
        elif type(obj) is str:
            if len(obj) == 1:
                if enclose: return APLArray(rho=[], data=[obj], type_hint=APLArray.TYPE_HINT_CHAR)
                else: return obj
            else:
                aplstr = APLArray.from_python(list(obj))
                aplstr.type_hint = APLArray.TYPE_HINT_CHAR
                return aplstr

        elif type(obj) is bytes:
            # a non-unicode string will be encoded as UTF-8
            return APLArray.from_python(str(obj, "utf8"))

        # if the object is iterable, but not one of the above, try making a list out of it
        if isinstance(obj, collections.Iterable):
            return APLArray.from_python(list(obj))

        # nothing else is supported for now
        raise TypeError("type not supported: " + repr(type(obj)))

    def copy(self):
        """Return an independent deep copy of the array."""
        rho = self.rho
        data = []
        for item in self.data:
            if isinstance(item, APLArray): data.append(item.copy())
            else: data.append(item)

        return APLArray(rho, data, self.genTypeHint())

    def __eq__(self, other):
        if self.rho != self.rho: return False

        for (x,y) in zip(self.data, other.data):
            if x != y: return False

        return True

    def __ne__(self, other):
        return not (self == other)

    def split(self, nocopy=False):
        """APL ↓ - used by the conversion method
        
        If nocopy is set, no deep copy of the objects is made. This *will* leave
        several arrays pointing into the same memory - be warned and do not mutate
        the result if you use this. 
        """

        if len(self.rho)==0: return self if nocopy else self.copy() # no difference on scalars
        elif len(self.rho)==1: 
            # equivalent to enclose
            arr=self if nocopy else self.copy()
            return APLArray(rho=[], data=[self], type_hint=self.genTypeHint())
        else:
            newrho = self.rho[:-1]
            blocksz = self.rho[-1]
            nblocks = product(newrho)
            newdata = []

            for blockn in range(nblocks):
                blockdata = []
                offset = blocksz*blockn
                for blockitem in range(blocksz):
                    item = self.data[offset + blockitem]
                    if isinstance(item, APLArray) and not nocopy: item=item.copy()
                    blockdata.append(item)

                newdata.append(APLArray(rho=[blocksz], data=blockdata, type_hint=self.genTypeHint()))

            return APLArray(rho=newrho, data=newdata, type_hint=self.genTypeHint())
        
    def genTypeHint(self):
        if not self.type_hint is None:
            # it already exists
            return self.type_hint
        elif len(self.data)!=0:
            # we have some data to use
            if isinstance(self.data[0], APLArray):
                self.type_hint = self.data[0].genTypeHint()
            elif type(self.data[0]) in (str,bytes):
                self.type_hint = APLArray.TYPE_HINT_CHAR
            else:
                self.type_hint = APLArray.TYPE_HINT_NUM
        else:
            # if we can't deduce anything, assume numeric empty vector
            self.type_hint = APLArray.TYPE_HINT_NUM
        return self.type_hint

    def __init__(self, rho, data, type_hint=None):
        self.rho=rho
        self.data=extend(list(data), product(rho))
        # deduce type from data
        if not type_hint is None:
            # hint is given
            self.type_hint = type_hint
        else:
            self.type_hint = self.genTypeHint()

    def flatten_idx(self, idx, IO=0):
        return sum((x-IO)*(y-IO) for x,y in zip(scan_reverse(operator.__mul__,self.rho[1:]+[1]), idx))

    def check_valid_idx(self, idx):
        if type(idx) in (int,long): # if ⍴=1, allow for index to be given as scalar
            idx = [idx]

        if not len(idx)==len(self.rho):
            raise IndexError("⍴=%d, should be %d"%(len(self.rho),len(idx)))
        
        if not all(0 <= ix < sz for (ix,sz) in zip(idx, self.rho)):
            raise IndexError()

        return idx

    def __getitem__(self,idx):
        idx = self.check_valid_idx(idx)
        return self.data[self.flatten_idx(idx)]

    def __setitem__(self,idx,val):
        idx = self.check_valid_idx(idx)
        # make sure that if arrays are added, they are converted transparently
        self.data[self.flatten_idx(idx)]=APLArray.from_python(val,enclose=False)

    def toJSONString(self):
        return json.dumps(self, cls=ArrayEncoder, ensure_ascii=False)

    @staticmethod 
    def fromJSONString(string):
        if type(string) is bytes: string = str(string, 'utf8')
        return APLArray._json_decoder.decode(string)

# serialize an array using JSON
class ArrayEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, APLArray):
            return {"r": obj.rho, "d": obj.data, "t":obj.genTypeHint()}
        elif isinstance(obj, APLNamespace):
            return {"ns": obj.dct}
        elif isinstance(obj, complex):
            return {"real": obj.real, "imag": obj.imag}
        else:
            return json.JSONEncoder.default(self, obj)

