from __future__ import annotations

import collections
import json
from abc import ABC, abstractmethod
from math import prod
from typing import Any, Dict, Iterable, NewType


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
        """Turns a JSON-like dictionary into the corresponding JSONAware object.

        Typically, this function isn't called directly.
        It is the JSON decoder's responsibility to call this function when needed.
        The only argument to this function is the JSON-like dictionary that represents
        the JSON-serialisable version of an object of the current type.
        """
        raise NotImplementedError()


class JSONAwareEncoder(json.JSONEncoder):
    """JSON encoder for all objects that are JSONAware."""

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

    When subclassing APLProxy, you must provide the appropriate class method that builds
    the given type of APL proxy from the supported Python objects.
    """

    def __new__(cls, obj: Any) -> APLProxy | int | float:
        """Construct an appropriate APLProxy for the given Python object.

        This will leave some basic types unchanged, like integers, because those
        elementary types do not need to be proxied.
        """

        if isinstance(obj, (int, float)):
            return obj
        elif isinstance(obj, dict):
            return APLNamespace.from_python(obj)
        elif isinstance(obj, Iterable):
            return APLArray.from_python(obj)
        return cls.from_python(obj)

    @classmethod
    def from_python(cls, obj: Any) -> APLProxy:
        """Build the APL proxy that best represents the given Python object."""
        raise NotImplementedError()

    def to_python(self) -> Any:
        """Build the closest native Python representation of the given APLProxy."""
        raise NotImplementedError()


class APLNamespace(APLProxy, JSONAware):
    """Proxy for APL namespaces, which are emulated as dictionaries with string keys.

    When creating APLNamespace proxies from Python dictionaries, keep in mind that
    the keys of the dictionaries that create APLNamespace instances must be strings
    because the dictionary keys mimic the dotted access of namespace values. For example,
    if `ns` is an APL namespace, `ns.foo ← 73` sets the variable `foo` from the namespace
    `ns` to `73`. The values of the dictionary can be arbitrary and will be converted
    to the appropriate APL proxy objects.
    """

    @classmethod
    def from_python(cls, data: dict[str, Any]) -> APLNamespace:
        """Build a proxy for an APL namespace from a Python dictionary."""

        self = object.__new__(cls)
        for key, value in data.items():
            setattr(self, key, value)
        return self

    def to_python(self) -> dict[str, Any]:
        """Convert the APL namespace into a plain Python dictionary."""

        dict_ = {}
        for key, value in self.__dict__.items():
            if isinstance(value, APLProxy):
                dict_[key] = value.to_python()
                continue

            dict_[key] = value

        return dict_

    def _to_json(self) -> JSONDict:
        """Convert the APL namespace proxy into a JSON-serialisable object.

        Because APL namespaces can contain arbitrary objects as the values associated
        with string keys, we need to traverse the data of the namespace and ensure
        we convert it to a JSON-serialisable object when needed.
        """

        json_data: Any = {}
        for key, value in self.__dict__.items():
            print(f"{key = } {value = }")
            if isinstance(value, JSONAware):
                json_data[key] = value.to_json()
                continue

            json_data[key] = value

        return JSONDict({"__dict__": json_data})

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> APLNamespace:
        """"""
        self = object.__new__(cls)
        for key, value in json["__dict__"].items():
            setattr(self, key, value)
        return self

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.__dict__})"

    def __eq__(self, other: Any) -> bool:
        """Compare two APL namespace proxies by comparing their values."""
        return isinstance(other, type(self)) and self.__dict__ == other.__dict__


class APLArray(APLProxy, JSONAware):
    """Proxy for APL arrays, which are emulated as (nested) lists."""

    shape: list[int]
    data: list[Any]

    @classmethod
    def from_python(
        cls, data: Iterable[Any], shape: list[int] | None = None
    ) -> APLArray:
        """Build a proxy APL array from a Python iterable."""

        self = object.__new__(cls)

        # Traverse the data given and build the appropriate proxies.
        # Special case for when the data is a string to prevent infinite recursion.
        if isinstance(data, str):
            self.data = list(data)
        else:
            self.data = [APLProxy(obj) for obj in data]

        # Compute shape if needed, in which case assume we have a vector.
        shape = [len(self.data)] if shape is None else shape
        if prod(shape) != len(self.data):
            raise ValueError(
                f"{cls} shape {shape} and data length {prod(shape)} mismatch."
            )
        self.shape = shape

        return self

    def to_python(self) -> list[Any]:
        """Convert the APL array into a Python list.

        In its Python representation, both nesting and rank are encoded by sublists.
        This means that multiple APL arrays end up being represented in the same way.
        """

        # If the rank is 0 or 1, return the flat data as-is.
        if len(self.shape) <= 1:
            return [
                value.to_python() if isinstance(value, APLProxy) else value
                for value in self.data
            ]
        # Otherwise, use recursion to nest the data.
        else:
            sub_shape = self.shape[1:]
            sub_len = prod(self.shape) // self.shape[0]
            return [
                APLArray.from_python(
                    self.data[i * sub_len : (i + 1) * sub_len], sub_shape
                ).to_python()
                for i in range(self.shape[0])
            ]

    def _to_json(self) -> JSONDict:
        return JSONDict(
            {
                "shape": self.shape,
                "data": [
                    value.to_json() if isinstance(value, JSONAware) else value
                    for value in self.data
                ],
            }
        )

    @classmethod
    def from_json(cls, json: JSONDict) -> APLArray:
        self = object.__new__(cls)
        self.shape = json["shape"]
        self.data = json["data"]
        if prod(json["shape"]) != len(json["data"]):
            raise ValueError(
                f"{cls} shape {self.shape} and data length {prod(self.shape)} mismatch."
            )
        return self

    def __eq__(self, other: Any) -> bool:
        return (
            isinstance(other, type(self))
            and self.shape == other.shape
            and self.data == other.data
        )


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
