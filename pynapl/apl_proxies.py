from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


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


class SendableMixin(ABC):
    """Mixin for the APL proxy objects that can be sent to APL."""

    @abstractmethod
    def to_json(self) -> dict[str, Any]:
        """Converts a Sendable object to a JSON-like dictionary."""
        raise NotImplementedError()


class ReceivableMixin(ABC):
    """Mixin for the APL proxy objects that can be received directly from APL."""

    @classmethod
    @abstractmethod
    def from_json(cls, json: dict[str, Any]) -> APLProxy:
        raise NotImplementedError()


class APLNamespace(APLProxy, SendableMixin, ReceivableMixin):
    """Proxy for APL namespaces, which are emulated as dictionaries with string keys."""

    @classmethod
    def from_python(cls, obj: dict[str, Any]) -> APLNamespace:
        self = object.__new__(cls)
        for attr, value in obj.items():
            setattr(self, attr, value)
        return self

    def to_python(self) -> dict[str, Any]:
        raise NotImplementedError()

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> APLNamespace:
        raise NotImplementedError()

    def to_json(self) -> dict[str, Any]:
        return vars(self)


class APLArray(APLProxy, SendableMixin, ReceivableMixin):
    """Proxy for APL arrays, which are emulated as (nested) lists."""
