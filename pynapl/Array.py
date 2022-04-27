from __future__ import annotations


import json
import operator
import sys
from abc import ABC, abstractmethod
from collections.abc import Iterable
from itertools import accumulate
from typing import Any, Callable, Reversible, TypeVar
from math import prod

try:
    import numpy as np

    NUMPY_SUPPORT = True
except ImportError:
    NUMPY_SUPPORT = False

from .ObjectWrapper import ObjectRef, ObjectWrapper


T = TypeVar("T")


class Sendable(ABC):
    """Class to be inherited by objects that we want to be able to send to APL.

    Sendables know how to convert to JSON-like Python dictionaries with string keys
    and with values that the module json knows how to convert."""

    @abstractmethod
    def to_json(self) -> dict[str, Any]:
        """Converts a Sendable object to a JSON-like dictionary."""
        raise NotImplementedError()

    def dumps(self) -> str:
        """Converts a Sendable object to a JSON string."""
        return json.dumps(self.to_json(), cls=ArrayEncoder, ensure_ascii=False)


class Receivable(ABC):
    """Class to be inherited by objects that we might receive from APL."""

    @abstractmethod
    def to_python(self, apl=None):
        raise NotImplementedError()


class ArrayEncoder(json.JSONEncoder):
    """JSON encoder for instances of APLArray."""

    def default(self, obj):
        if isinstance(obj, Sendable):
            return obj.to_json()
        elif isinstance(obj, complex):  # special-cased
            return {"real": obj.real, "imag": obj.imag}
        else:
            return json.JSONEncoder.default(self, obj)


def _json_object_hook(jsobj):
    # if this is an APL array, return it as such

    if isinstance(jsobj, dict):
        if "r" in jsobj and "d" in jsobj:
            # this is an APL array
            type_hint = APLArray.TYPE_HINT_NUM
            if "t" in jsobj:
                type_hint = jsobj["t"]
            return APLArray(jsobj["r"], list(jsobj["d"]), type_hint=type_hint)
        elif "ns" in jsobj:
            # this is an APL namespace, which can be represented as a dict in Python
            return APLNamespace(jsobj["ns"])
        elif "id" in jsobj:
            # this is a reference to an APL object
            return APLObjectFactory(jsobj)
        elif "rid" in jsobj:
            # this is a reference to a Python object sent over APL
            return ObjectRef(jsobj["rid"])
        elif "imag" in jsobj:
            # this is a complex number
            return complex(jsobj["real"], jsobj["imag"])
        else:
            return jsobj
    else:
        return jsobj


ArrayDecoder = json.JSONDecoder(object_hook=_json_object_hook)


def scan_reverse(f: Callable[[T, T], T], arr: Reversible[T]) -> Iterable[T]:
    """Scan over a list in reverse, using a function."""
    return reversed(list(accumulate(reversed(arr), lambda x, y: f(y, x))))


def extend(arr: list[T], length: int) -> list[T]:
    """Extend a list APL-style."""

    r = arr[:]
    if len(r) < length:
        while length - len(r) >= len(arr):
            r.extend(arr)
        r.extend(arr[: length - len(r)])
    return r[:length]


# assuming ⎕IO=0 for now
class APLNamespace(Sendable, Receivable):
    def __init__(self, dct: dict[str, APLArray] | None = None, apl=None):
        self.dct = dct if dct is not None else {}
        self.apl = apl

    def __getitem__(self, key: str) -> APLArray:
        return self.dct[key]

    def __setitem__(self, key: str, val: Any):
        self.dct[key] = APLArray.from_python(val, enclose=False, apl=self.apl)

    def to_json(self):
        return {"ns": self.dct}

    # convert an APL namespace to a Python dictionary
    def to_python(self, apl=None):
        newdct = {}
        for x in self.dct:
            obj = self.dct[x]
            if isinstance(obj, Receivable):
                newdct[x] = obj.to_python(apl)
            else:
                newdct[x] = obj
        return newdct

    @staticmethod
    # convert a Python dictionary to an APL namespace
    def from_python(dct, apl=None):
        newdct = {}
        for x in dct:
            newdct[x] = APLArray.from_python(dct[x], apl=apl)
        return APLNamespace(newdct, apl=apl)

    @staticmethod
    def fromJSONString(string):
        return ArrayDecoder.decode(string)


class APLObjectFactory(Receivable):
    """Makes an APL object."""

    def __init__(self, dct):
        self.__id = dct["id"]
        self.__va = dct["va"]
        self.__fn = dct["fn"]
        self.__invalid = False

    def to_python(self, apl):
        if not self.__invalid:
            self.__invalid = True  # only use once
            return APLObject(apl, self.__id, self.__va, self.__fn)
        else:
            raise RuntimeError("Tried to use the same reference more than once.")


class APLObject(Sendable):
    """Can be used to interact with an APL object."""

    def __init__(self, apl, id, va, fn):
        self.__s = {"apl": apl, "id": id, "va": va, "fn": fn}

        # create function stubs
        for f in fn:
            fname = f
            # In Python 2, f must be ASCII-encoded - this is lossy, so APL class members that
            # have non-ASCII names get their names mangled
            if sys.version_info.major == 2:
                fname = f.encode("ascii", "replace")

            object.__setattr__(self, fname, apl.fn("(py.⍙Access'%s').%s" % (id, f)))

    def __getattr__(self, name):
        if name == "_APLObject__s":
            return object.__getattribute__(self, name)

        elif name in self.__s["va"]:
            # retrieve the value from APL instead
            return self.__s["apl"].eval("(py.⍙Access'%s').%s" % (self.__s["id"], name))
        elif name in self.__s["fn"] or name.startswith("_"):
            return object.__getattribute__(self, name)
        else:
            raise AttributeError("No such field: %s" % name)

    def __setattr__(self, name, value):
        if name == "_APLObject__s":
            object.__setattr__(self, name, value)
        elif name in self.__s["va"]:
            # set the value on the APL side
            self.__s["apl"].fn("{(py.⍙Access'%s').%s ← ⍵}" % (self.__s["id"], name))(
                value
            )
        else:
            raise AttributeError("No such field: %s" % name)

    def __del__(self):
        # try to tell the APL instance to free this object, if it still exists
        # it may already be shut down, so don't throw any errors
        try:
            self.__s["apl"].fn("py.⍙Release")(self.__s["id"])
        except:
            pass

    def to_json(self):
        return {"rid": self.__s["id"]}

    def to_python(self, apl=None):
        if not apl in [None, self.__s["apl"]]:
            raise RuntimeError(
                "changing the APL interpreter instance out from under an object is not supported"
            )

        return self  # this already is an usable object


class APLArray(Sendable, Receivable):
    """Serializable multidimensional array.

    Every element of the array must be either a value or another array.
    """

    TYPE_HINT_NUM = 0
    TYPE_HINT_CHAR = 1

    data = None
    rho = None
    type_hint = None

    # convert array to suitable-ish python representation
    def to_python(self, apl=None):
        """Convert an APLArray to a Python object.

        Multidimensional arrays will be split up row-by-row and returned as a nested list,
        as if one had done ↓."""

        if len(self.rho) == 0:  # scalar
            scalar = self.data[0]
            if isinstance(scalar, Receivable):
                return scalar.to_python(apl)
            else:
                return scalar

        elif len(self.rho) == 1:  # array
            # if the type hint says characters, and the array is simple, return a string
            if self.genTypeHint() == APLArray.TYPE_HINT_CHAR and not any(
                isinstance(x, (Sendable, Receivable)) for x in self.data
            ):
                return "".join(self.data)

            # if not, return a list. If this is a nested array that _does_ have a simple
            # string in it somewhere, *that* string *will* show up as a string within the
            # converted object
            else:
                pylist = []
                for item in self.data:
                    if isinstance(item, Receivable):
                        item = item.to_python(apl)

                    pylist.append(item)
                return pylist

        elif len(self.rho) >= 2:  # higher-rank array
            # split the array until it is entirely flat
            arr = self
            # nocopy is safe here because arr is never modified
            while len(arr.rho) > 0:
                arr = arr.split(nocopy=True)
            # convert the flattened array to a python representation
            return arr.to_python(apl)

        raise RuntimeError("rho < 0; rho=%d!" % self.rho)

    @staticmethod
    def from_python(obj, enclose=True, apl=None):
        """Create an APLArray from a Python object.

        Objects may be numbers, strings, or lists.

        If the object is already an APLArray, it will be returned unchanged.
        """

        if obj is None:
            return APLArray.from_python([], apl=apl)  # Return the empty list for "None"

        if NUMPY_SUPPORT:
            # special case this
            if isinstance(obj, np.matrix) or isinstance(obj, np.ndarray):
                shape = obj.shape
                rank = len(shape)
                l = obj.tolist()
                for i in range(rank - 1):
                    l = sum(l, [])

                l = [APLArray.from_python(x, False, apl) for x in l]
                return APLArray(rho=shape, data=l, apl=apl)

        if isinstance(obj, Sendable):
            return obj  # it already is of the right type

        if isinstance(obj, dict):
            # convert all items in the dictionary to APL representation
            return APLNamespace.from_python(obj, apl=apl)

        # lists, tuples and strings can be represented as vectors
        if isinstance(obj, (list, tuple)):
            return APLArray(
                rho=[len(obj)],
                data=[APLArray.from_python(x, False, apl) for x in obj],
                apl=apl,
            )

        # numbers can be represented as numbers, enclosed if at the upper level so we always send an 'array'
        elif isinstance(obj, (int, float, complex)):
            if enclose:
                return APLArray(
                    rho=[], data=[obj], type_hint=APLArray.TYPE_HINT_NUM, apl=apl
                )
            else:
                return obj

        # boolean scalars should convert to ints for APL's sake
        elif isinstance(obj, bool):
            return APLArray.from_python(int(obj), enclose, apl)

        # a one-element string is a character, a multi-element string is a vector
        elif isinstance(obj, str):
            if len(obj) == 1:
                if enclose:
                    return APLArray(
                        rho=[], data=[obj], type_hint=APLArray.TYPE_HINT_CHAR, apl=apl
                    )
                else:
                    return obj
            else:
                aplstr = APLArray.from_python(list(obj), False, apl)
                aplstr.type_hint = APLArray.TYPE_HINT_CHAR
                return aplstr

        elif isinstance(obj, bytes):
            # a non-unicode string will be encoded as UTF-8
            return APLArray.from_python(str(obj, "utf8"), enclose, apl)

        # if the object is iterable, but not one of the above, try making a list out of it
        if isinstance(obj, Iterable) or hasattr(obj, "__iter__"):
            return APLArray.from_python(list(obj), False, apl)

        # last ditch resort: if the object implements __len__ and __getitem__,
        # we can iterate over it and get the objects that way
        if hasattr(obj, "__len__") and hasattr(obj, "__getitem__"):
            try:
                ls = []
                for idx in range(len(obj)):
                    ls.append(obj[idx])
                return APLArray.from_python(ls, False, apl)
            except:
                # if an exception occurs while trying this, let's just report that
                # we don't support it.
                raise TypeError("type not supported: " + repr(type(obj)))

        if not apl is None:
            # Wrap the object, store it, send a reference
            return ObjectWrapper(apl.store, obj)
        else:
            # Nope
            raise TypeError("type not supported: " + repr(type(obj)))

    def copy(self):
        """Return an independent deep copy of the array."""
        rho = self.rho
        data = []
        for item in self.data:
            if isinstance(item, APLArray):
                data.append(item.copy())
            else:
                data.append(item)

        return APLArray(rho, data, self.genTypeHint(), apl=self.apl)

    def __eq__(self, other):
        if self.rho != self.rho:
            return False

        for (x, y) in zip(self.data, other.data):
            if x != y:
                return False

        return True

    def __ne__(self, other):
        return not (self == other)

    def split(self, nocopy=False):
        """APL ↓ - used by the conversion method

        If nocopy is set, no deep copy of the objects is made. This *will* leave
        several arrays pointing into the same memory - be warned and do not mutate
        the result if you use this.
        """

        if len(self.rho) == 0:
            return self if nocopy else self.copy()  # no difference on scalars
        elif len(self.rho) == 1:
            # equivalent to enclose
            arr = self if nocopy else self.copy()
            return APLArray(
                apl=self.apl, rho=[], data=[self], type_hint=self.genTypeHint()
            )
        else:
            newrho = self.rho[:-1]
            blocksz = self.rho[-1]
            nblocks = prod(newrho)
            newdata = []

            for blockn in range(nblocks):
                blockdata = []
                offset = blocksz * blockn
                for blockitem in range(blocksz):
                    item = self.data[offset + blockitem]
                    if isinstance(item, APLArray) and not nocopy:
                        item = item.copy()
                    blockdata.append(item)

                newdata.append(
                    APLArray(
                        apl=self.apl,
                        rho=[blocksz],
                        data=blockdata,
                        type_hint=self.genTypeHint(),
                    )
                )

            return APLArray(
                apl=self.apl, rho=newrho, data=newdata, type_hint=self.genTypeHint()
            )

    def genTypeHint(self):
        if not self.type_hint is None:
            # it already exists
            return self.type_hint
        elif len(self.data) != 0:
            # we have some data to use
            if isinstance(self.data[0], APLArray):
                self.type_hint = self.data[0].genTypeHint()
            elif isinstance(self.data[0], (str, bytes)):
                self.type_hint = APLArray.TYPE_HINT_CHAR
            else:
                self.type_hint = APLArray.TYPE_HINT_NUM
        else:
            # if we can't deduce anything, assume numeric empty vector
            self.type_hint = APLArray.TYPE_HINT_NUM
        return self.type_hint

    def __init__(self, rho, data, type_hint=None, apl=None):
        self.rho = rho
        self.apl = apl
        self.data = extend(list(data), prod(rho))
        # deduce type from data
        if not type_hint is None:
            # hint is given
            self.type_hint = type_hint
        else:
            self.type_hint = self.genTypeHint()

    def flatten_idx(self, idx, IO=0):
        return sum(
            (x - IO) * (y - IO)
            for x, y in zip(scan_reverse(operator.__mul__, self.rho[1:] + [1]), idx)
        )

    def check_valid_idx(self, idx):
        if isinstance(idx, int):  # if ⍴=1, allow for index to be given as scalar
            idx = [idx]

        if not len(idx) == len(self.rho):
            raise IndexError("⍴=%d, should be %d" % (len(self.rho), len(idx)))

        if not all(0 <= ix < sz for (ix, sz) in zip(idx, self.rho)):
            raise IndexError()

        return idx

    def __getitem__(self, idx):
        idx = self.check_valid_idx(idx)
        return self.data[self.flatten_idx(idx)]

    def __setitem__(self, idx, val):
        idx = self.check_valid_idx(idx)
        # make sure that if arrays are added, they are converted transparently
        self.data[self.flatten_idx(idx)] = APLArray.from_python(
            val, enclose=False, apl=self.apl
        )

    def to_json(self):
        return {"r": self.rho, "d": self.data, "t": self.genTypeHint()}

    @staticmethod
    def fromJSONString(string):
        if isinstance(string, bytes):
            string = str(string, "utf8")
        return ArrayDecoder.decode(string)
