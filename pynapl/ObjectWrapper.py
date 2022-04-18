# Object wrapper
# This allows a representation of a Python object to be sent over to
# APL

import sys

from .ConversionInterface import Sendable, Receivable

if sys.version_info.major == 2:
    bytes, str=str, unicode

# store and free object instances
class ObjectStore(object):
    """Stores instances of objects that APL knows about, so they can
    be retrieved by ID and aren't garbage-collected."""

    def __init__(self):
        self.objects = {}

    def store(self, obj):
        """Keep a reference to an object, return the reference."""
        ref = str(id(obj))

        # If we already have it, increase the refcount
        # (if you have to keep refcounts by hand in Python, you know you're
        # using it the way it was intended)

        if ref in self.objects:
            obj, refcount = self.objects[ref]
            self.objects[ref] = (obj, refcount+1)
        else:
            self.objects.update({ref: (obj, 1)})
        
        return ref

    def retrieve(self, ref):
        """Return a reference to an object, if we have it."""
        ref = str(ref)
        if not ref in self.objects:
            raise ValueError("No object with reference: %s"%ref)
        obj, refcount = self.objects[ref]
        return obj

    def release(self, ref):
        """Release an object, given a reference."""
        ref = str(ref)
        if not ref in self.objects:
            raise ValueError("No object with reference: %s"%ref)

        obj, refcount = self.objects[ref]
        if refcount<=1:
            # There are no more references to this object on the APL side,
            # so remove it.
            del self.objects[ref]
        else:
            self.objects[ref] = (obj, refcount-1)


# Wrap an object and store it in an object store
class ObjectWrapper(Sendable):
    
    def __init__(self, store, obj):
        self.__store = store
        self.__ref = store.store(obj)

    def ref(self):
        return self.__ref

    def items(self):
        """Return a list of variable names and function names """
        obj = self.__store.retrieve(self.__ref)
        classname = obj.__class__.__name__
        va=[]
        fn=[]

        for attr in dir(obj):

            try:
                item = getattr(obj, attr)
                if hasattr(item,'__call__'):
                    fn.append(attr)
                else:
                    va.append(attr)
            except (ImportError, NotImplementedError):
                # There are modules which import other modules conditionally,
                # which aren't necessarily available, but which would only give
                # an error if you actually tried to use it. Since this wrapper
                # pokes everything, it would trap all of that, so we catch
                # ImportError and ignore it. If something could not be imported,
                # it is simply not included in the list of attributes. 
                pass
            except (AttributeError, KeyError):
                # Some objects claim to have attributes (via `dir`), but then raise
                # AttributeError when you actually try to access them. These are
                # also ignored.
                # Some objects with custom __getattr__ methods wrongly raise
                # KeyError instead of AttributeError.
                pass

        return classname, va, fn

    def toJSONDict(self):
        cls, va, fn = self.items()
        return {"id": self.ref(), "cls": cls, "va": va, "fn": fn}

# only holds a reference, but can be used to retrieve the actual object
class ObjectRef(Receivable):
    def __init__(self, ref):
        self.ref = ref

    # to match the Array function.
    def to_python(self, apl):
        return apl.store.retrieve(self.ref)

