from __future__ import annotations

from typing import Any, Iterable

import pytest

from pynapl.proxies import APLArray, APLNamespace, APLProxy
import extendedjson as xjson


SIMPLE_DICTIONARIES_FOR_PARAMETRIZATION: list[dict[str, Any]] = [
    {},
    {"key": -3},
    {"foo": 73, "bar": True},
    {"foo": "hey", "bar": 73, "baz": False},
]


@pytest.mark.parametrize("dict_", SIMPLE_DICTIONARIES_FOR_PARAMETRIZATION)
def test_dict_proxy_creation(dict_: dict[str, Any]):
    """Tests that dictionaries are converted to APLNamespace objects."""
    assert isinstance(APLProxy(dict_), APLNamespace)


@pytest.mark.parametrize("dict_", SIMPLE_DICTIONARIES_FOR_PARAMETRIZATION)
def test_APLNamespace_python_roundtrip(dict_: dict[str, Any]):
    """Make sure dicts converted to APL proxies and back are round tripped."""
    assert APLNamespace.from_python(dict_).to_python() == dict_


@pytest.mark.parametrize("dict_", SIMPLE_DICTIONARIES_FOR_PARAMETRIZATION)
def test_APLNamespace_json_roundtrip(dict_: dict[str, Any]):
    """Make sure APLNamespace objects converted to/from JSON roundtrip properly."""

    ns = APLNamespace.from_python(dict_)
    assert xjson.loads(xjson.dumps(ns)) == ns
    ns_json = xjson.dumps(ns)
    assert xjson.dumps(xjson.loads(ns_json)) == ns_json


SIMPLE_ITERABLES_FOR_PARAMETRIZATION: list[Iterable] = [
    range(10),
    [5, 6, 7, 8],
    (-3, True, 73, False),
    "Hello, world!",
]


@pytest.mark.parametrize("iter_", SIMPLE_ITERABLES_FOR_PARAMETRIZATION)
def test_iterable_proxy_creation(iter_: Iterable):
    """Tests that iterables are converted to APLArray objects."""
    assert isinstance(APLProxy(iter_), APLArray)


@pytest.mark.parametrize("iter_", SIMPLE_ITERABLES_FOR_PARAMETRIZATION)
def test_APLArray_python_data_roundtrip(iter_: Iterable):
    """Make sure iterables converted to APL proxies and back round trip the data."""
    assert APLArray.from_python(iter_).to_python() == list(iter_)


@pytest.mark.parametrize("iter_", SIMPLE_ITERABLES_FOR_PARAMETRIZATION)
def test_APLArray_json_roundtrip(iter_: Iterable):
    """Make sure APLArray objects converted to/from JSON roundtrip properly."""

    ns = APLArray.from_python(iter_).to_python()
    assert xjson.loads(xjson.dumps(ns)) == ns
    ns_json = xjson.dumps(ns)
    assert xjson.dumps(xjson.loads(ns_json)) == ns_json


def test_APLArray_creation_with_nesting():
    """Make sure APLArray behaves appropriately for nested Python iterables."""

    data = [[True, False, True], [], [1, 2, [3, 4, [5, 6]]]]
    arr = APLArray.from_python(data)
    assert arr.to_python() == data
    arr_json = xjson.dumps(arr.to_python())
    assert xjson.dumps(xjson.loads(arr_json)) == arr_json
