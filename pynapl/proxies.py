from __future__ import annotations

from math import prod
from typing import Any, Dict, Iterable, NewType

import extendedjson as xjson


JSONDict = NewType("JSONDict", Dict[str, Any])


class APLProxy:
    """Base class for all objects that can be used to proxy APL entities.

    An APLProxy object is an object that provides a Python interface that emulates
    the native APL behaviour with respect to some APL built-in.
    For example, APL has native support for multi-dimensional arrays while Python has not.
    Thus, we provide APLArray as a proxy for APL's arrays.

    When subclassing APLProxy, you must provide the appropriate class method that builds
    the given type of APL proxy from the supported Python objects.
    """

    def __new__(cls, obj: Any, *args, **kwargs) -> APLProxy | int | float:
        """Construct an appropriate APLProxy for the given Python object.

        This will leave some basic types unchanged, like integers, because those
        elementary types do not need to be proxied.
        """

        if isinstance(obj, (int, float)):
            return obj
        elif isinstance(obj, dict):
            return APLNamespace.from_python(obj, *args, **kwargs)
        elif isinstance(obj, Iterable):
            return APLArray.from_python(obj, *args, **kwargs)
        return cls.from_python(obj, *args, **kwargs)

    @classmethod
    def from_python(cls, obj: Any) -> APLProxy:
        """Build the APL proxy that best represents the given Python object."""
        raise NotImplementedError()

    def to_python(self) -> Any:
        """Build the closest native Python representation of the given APLProxy."""
        raise NotImplementedError()


class APLNamespace(APLProxy):
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

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.__dict__})"

    def __eq__(self, other: Any) -> bool:
        """Compare two APL namespace proxies by comparing their values."""
        return isinstance(other, type(self)) and self.__dict__ == other.__dict__


class APLArray(APLProxy):
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

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.data}, {self.shape})"

    def __eq__(self, other: Any) -> bool:
        return (
            isinstance(other, type(self))
            and self.shape == other.shape
            and self.data == other.data
        )


@xjson.register_encoder
class PynAPLEncoder(xjson.ExtendedEncoder):
    def encode_complex(self, c: complex) -> JSONDict:
        return JSONDict({"real": c.real, "imag": c.imag})

    def encode_APLNamespace(self, ns: APLNamespace) -> JSONDict:
        return JSONDict(
            {
                "ns": {
                    key: self.default(value) if isinstance(value, APLProxy) else value
                    for key, value in ns.__dict__.items()
                }
            }
        )

    def encode_APLArray(self, array: APLArray) -> JSONDict:
        return JSONDict(
            {
                "shape": array.shape,
                "data": [
                    self.default(value) if isinstance(value, APLProxy) else value
                    for value in array.data
                ],
            }
        )


@xjson.register_decoder
class PynAPLDecoder(xjson.ExtendedDecoder):
    def decode_complex(self, obj: JSONDict) -> complex:
        return complex(float(obj["real"]), float(obj["imag"]))

    def decode_APLNamespace(self, obj: JSONDict) -> APLNamespace:
        return APLNamespace.from_python(obj["ns"])

    def decode_APLArray(self, obj: JSONDict) -> APLArray:
        return APLArray.from_python(obj["data"], obj["shape"])


if __name__ == "__main__":
    ns_ = APLNamespace({"hey": 73, "bool": True})
    ns = APLNamespace({"ho": 1, "sub_ns": ns_})
    print(s := xjson.dumps(ns))
    print(xjson.loads(s))
