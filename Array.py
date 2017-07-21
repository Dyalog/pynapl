# -*- coding: utf-8 -*-


import operator
import json
import codecs
import collections

from Util import *

# assuming ⎕IO=0 for now
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
        
        if type(jsobj) is dict \
        and 'r' in jsobj \
        and 'd' in jsobj:
            type_hint = APLArray.TYPE_HINT_NUM
            if 't' in jsobj: type_hint = jsobj['t']
            return APLArray(jsobj['r'], list(jsobj['d']), type_hint=type_hint)

        else:
            return jsobj
    
    # define a reusable json decoder
    __json_decoder = json.JSONDecoder(encoding="utf8", object_hook=__json_object_hook)

    # convert array to suitable-ish python representation
    def to_python(self):
        """Convert an APLArray to a Python object.

        Multidimensional arrays will be split up row-by-row and returned as a nested list, 
        as if one had done ↓."""

        if len(self.rho)==0: # scalar
            scalar = self.data[0]
            if isinstance(scalar, APLArray): return scalar.to_python()
            else: return scalar

        elif len(self.rho)==1: # array
            # if the type hint says characters, and the array is simple, return a string
            if self.genTypeHint() == APLArray.TYPE_HINT_CHAR \
            and not any(isinstance(x, APLArray) for x in self.data):
                return ''.join(self.data)

            # if not, return a list. If this is a nested array that _does_ have a simple
            # string in it somewhere, *that* string *will* show up as a string within the
            # converted object
            else:
                pylist = []
                for item in self.data:
                    if isinstance(item,APLArray): item=item.to_python()
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

        if isinstance(obj, APLArray):
            return obj # it already is of the right type

        # lists, tuples and strings can be represented as vectors
        if type(obj) in (list,tuple):
            return APLArray(rho=[len(obj)], 
                            data=[APLArray.from_python(x,enclose=False) for x in obj])
        
        # numbers can be represented as numbers, enclosed if at the upper level so we always send an 'array'
        elif type(obj) in (int,long,float): # complex not supported for now
            if enclose: return APLArray(rho=[], data=[obj], type_hint=APLArray.TYPE_HINT_NUM)
            else: return obj

        # boolean scalars should convert to ints for APL's sake
        elif type(obj) is bool:
            return APLArray.from_python(int(obj))

        # a one-element string is a character, a multi-element string is a vector
        elif type(obj) is unicode:
            if len(obj) == 1:
                if enclose: return APLArray(rho=[], data=[obj], type_hint=APLArray.TYPE_HINT_CHAR)
                else: return obj
            else:
                aplstr = APLArray.from_python(list(obj))
                aplstr.type_hint = APLArray.TYPE_HINT_CHAR
                return aplstr

        elif type(obj) is str:
            # a non-unicode string will be encoded as UTF-8
            return APLArray.from_python(unicode(obj, "utf8"))

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
            elif type(self.data[0]) in (str,unicode):
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
        if not len(idx)==len(self.rho):
            raise IndexError("⍴=%d, should be %d"%len(self.rho),len(idx))
        
        if not all(0 <= ix < sz for (ix,sz) in zip(idx, self.rho)):
            raise IndexError()


    def __getitem__(self,idx):
        self.check_valid_idx(idx)
        return self.data[self.flatten_idx(idx)]

    def __setitem__(self,idx,val):
        self.check_valid_idx(idx)
        # make sure that if arrays are added, they are converted transparently
        self.data[self.flatten_idx(idx)]=APLArray.from_python(val,enclose=False)

    def toJSONString(self):
        return json.dumps(self, cls=ArrayEncoder, ensure_ascii=False)

    @staticmethod 
    def fromJSONString(string):
        return APLArray.__json_decoder.decode(string)

# serialize an array using JSON
class ArrayEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, APLArray):
            return {"r": obj.rho, "d": obj.data, "t":obj.genTypeHint()}
        else:
            return json.JSONEncoder.default(obj)

