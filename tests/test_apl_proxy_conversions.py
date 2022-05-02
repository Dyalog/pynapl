from __future__ import annotations

from typing import Any

import pytest

from pynapl.apl_proxies import APLProxy, APLNamespace


SIMPLE_DICTIONARIES_FOR_PARAMETRIZATION: list[dict[str, Any]] = [
    {},
    {"key": -3},
    {"foo": 73, "bar": True},
    {"foo": "hey", "bar": 73, "baz": False},
]


@pytest.mark.parametrize("dict_", SIMPLE_DICTIONARIES_FOR_PARAMETRIZATION)
def test_dict_proxy_creation(dict_):
    """Tests that dictionaries are converted to APLNamespace APL proxy objects."""
    assert isinstance(APLProxy(dict_), APLNamespace)


@pytest.mark.parametrize("dict_", SIMPLE_DICTIONARIES_FOR_PARAMETRIZATION)
def test_APLNamespace_python_roundtrip(dict_):
    """Make sure dicts converted to APL proxies and back are round tripped."""
    assert APLProxy(dict_).to_python() == dict_


def test_APLNamespace_json_roundtrip(dict_):
    """Make sure APLNamespace objects converted to/from JSON roundtrip properly."""

    ns = APLNamespace.from_python(dict_)
    assert APLNamespace.from_json(APLNamespace.from_python(dict_).to_json()) == ns
    ns_json = ns.to_json()
    assert APLNamespace.from_json(ns_json).to_json() == ns
