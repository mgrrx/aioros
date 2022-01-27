import pytest

from aioros.master._param_cache import ParamCache


@pytest.fixture(name="some_parameters")
def fixture_some_parameters() -> ParamCache:
    cache = ParamCache()
    cache["/foo"] = "bar"
    cache["/bar"] = "foo"
    cache["/foobar/a"] = True
    cache["/foobar/b"] = False
    cache["/a/b/c/d/e/f"] = "g"
    cache["/list"] = [1, 2, 3]

    return cache


def test_setitem(some_parameters: ParamCache) -> None:
    assert some_parameters["/foo"] == "bar"
    some_parameters["/foo"] = "foo"
    assert some_parameters["/foo"] == "foo"
    some_parameters["/list"] = {}
    assert some_parameters["/list"] == {}


def test_getitem(some_parameters: ParamCache) -> None:
    assert some_parameters["/foo"] == "bar"
    assert some_parameters["/bar"] == "foo"
    assert some_parameters["/foobar"] == dict(a=True, b=False)
    assert some_parameters["/list"] == [1, 2, 3]
    assert some_parameters["/"] == dict(
        foo="bar",
        bar="foo",
        foobar=dict(a=True, b=False),
        list=[1, 2, 3],
        a=dict(b=dict(c=dict(d=dict(e=dict(f="g"))))),
    )


def test_contains(some_parameters: ParamCache) -> None:
    assert "/foo" in some_parameters
    assert "/foobar" in some_parameters
    assert "/foobar/a" in some_parameters
    assert "/foobar/b" in some_parameters
    assert "/foobar/c" not in some_parameters


def test_delete(some_parameters: ParamCache) -> None:
    assert "/foo" in some_parameters
    del some_parameters["/foo"]
    assert "/foo" not in some_parameters

    assert "/foobar" in some_parameters
    del some_parameters["/foobar/a"]
    assert "/foobar" in some_parameters
    assert "/foobar/a" not in some_parameters
    del some_parameters["/a/b/c/d/e/f"]
    assert set(some_parameters.keys()) == {"/bar", "/foobar/b", "/list"}


def test_keys(some_parameters: ParamCache) -> None:
    assert set(some_parameters.keys()) == {
        "/foo",
        "/bar",
        "/foobar/a",
        "/foobar/b",
        "/list",
        "/a/b/c/d/e/f",
    }


# TODO search
