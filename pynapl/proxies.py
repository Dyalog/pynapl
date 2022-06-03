from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, Dict, NewType


JSONDict = NewType("JSONDict", Dict[str, Any])


class JSONAware(ABC):
    """Mixin for Python objects that can be converted to and from JSON."""

    def to_json(self) -> JSONDict:
        """Converts an object to a JSON-serialisable dictionary.

        This function should not be overridden by subclasses;
        instead, subclasses should override `_to_json`.
        This class makes sure that the JSON-serialisable dictionary
        has the format needed so that the JSON can be loaded back as Python.
        """

        json_dict = self._to_json()
        print(type(self))
        json_dict["__json_aware_cls__"] = type(self).__name__
        return json_dict

    @abstractmethod
    def _to_json(self) -> JSONDict:
        """Converts an object to a JSON-serialisable dictionary."""
        raise NotImplementedError()

    @classmethod
    @abstractmethod
    def from_json(cls, json: JSONDict) -> JSONAware:
        """Turns a JSON-like dictionary into the corresponding JSONAware object."""
        raise NotImplementedError()


class JSONAwareEncoder(json.JSONEncoder):
    """JSON encoder for all objects that are sendable."""

    def default(self, obj: Any) -> JSONDict:
        if isinstance(obj, JSONAware):
            return obj.to_json()

        return super().default(obj)


class JSONAwareDecoder(json.JSONDecoder):
    """JSON decoder for representations of JSONAware objects."""

    def __init__(self, **kwargs):
        kwargs["object_hook"] = self.object_hook
        super().__init__(**kwargs)

    def object_hook(self, obj: JSONDict) -> JSONAware | JSONDict:
        try:
            cls = globals()[obj["__json_aware_cls__"]]
        except KeyError:
            return obj
        else:
            return cls.from_json(obj)


class APLProxy:
    """Base class for all objects that can be used to proxy APL entities.

    An APLProxy object is an object that provides a Python interface that emulates
    the native APL behaviour with respect to some APL built-in.
    For example, APL has native support for multi-dimensional arrays while Python has not.
    Thus, we provide APLArray as a proxy for APL's arrays.

    Subclasses of APLProxy must provide the appropriate class method that builds
    the given type of APL proxy from the supported Python objects.
    """

    def __new__(cls, *args, **kwargs) -> APLProxy:
        """Construct an appropriate APLProxy for the given Python object."""
        print(f"APLProxy __new__ {cls = }")

        return cls.from_python(*args, **kwargs)

    @classmethod
    def from_python(cls, obj: Any) -> APLProxy:
        """Build the APL proxy that best represents the given Python object."""
        print(f"APLProxy from_python {cls = }")
        raise NotImplementedError()

    def to_python(self) -> Any:
        """Build the closest native Python representation of the given APLProxy."""
        raise NotImplementedError()


class APLNamespace(APLProxy, JSONAware):
    """Proxy for APL namespaces, which are emulated as dictionaries with string keys."""

    data: dict[str, Any]

    @classmethod
    def from_python(cls, data: dict[str, Any]) -> APLNamespace:
        self = object.__new__(cls)
        self.data = data
        return self

    def to_python(self) -> dict[str, Any]:
        raise NotImplementedError()

    def _to_json(self) -> JSONDict:

        json_data: Any = {}
        for key, value in self.data.items():
            print(f"{key = } {value = }")
            if isinstance(value, JSONAware):
                json_data[key] = value.to_json()
                continue

            json_data[key] = value

        return JSONDict({"data": json_data})

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> APLNamespace:
        self = object.__new__(cls)
        self.data = json["data"]
        return self


class APLArray(APLProxy, JSONAware):
    """Proxy for APL arrays, which are emulated as (nested) lists."""


def load(*args, **kwargs):
    """`json.load` stub using the custom JSONAwareDecoder."""
    kwargs.setdefault("cls", JSONAwareDecoder)
    return json.load(*args, **kwargs)


def loads(*args, **kwargs):
    kwargs.setdefault("cls", JSONAwareDecoder)
    return json.loads(*args, **kwargs)


def dump(*args, **kwargs):
    kwargs.setdefault("cls", JSONAwareEncoder)
    return json.dump(*args, **kwargs)


def dumps(*args, **kwargs):
    kwargs.setdefault("cls", JSONAwareEncoder)
    return json.dumps(*args, **kwargs)


if __name__ == "__main__":
    ns_ = APLNamespace({"hey": 73, "bool": True})
    ns = APLNamespace({"ho": 1, "ns": ns_})
    print(ns)
    print(s := dumps(ns))
    print(loads(s))
    print(loads(s).data)
    print(loads(s).data["ns"].data)
