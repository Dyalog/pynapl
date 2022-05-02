from pynapl.apl_proxies import APLProxy, APLNamespace


def test_dict_proxy_creation():
    """Tests that dictionaries are converted to APLNamespace APL proxy objects."""

    assert isinstance(APLProxy(dict()), APLNamespace)
    assert isinstance(
        APLProxy({"foo": 73, "bar": False}),
        APLNamespace,
    )
