import os
import sys
from typing import Dict, List

import pytest
from pytest_mock import MockerFixture

from aioros._utils._resolve import (
    get_local_address,
    get_mappings,
    get_master_uri,
    get_namespace,
    get_remapped_name,
    normalize_namespace,
    resolve_name,
    validate_namespace,
)

ArgvType = List[str]
EnvType = Dict[str, str]


@pytest.mark.parametrize(
    ("argv", "environ", "expected"),
    [
        ([], {}, "http://localhost:11311"),
        (["__master:=foobar"], {}, "foobar"),
        (["__master:=foo", "__master:=bar"], {}, "foo"),
        (["__master:=foo"], {"ROS_MASTER_URI": "bar"}, "foo"),
        ([], {"ROS_MASTER_URI": "bar"}, "bar"),
    ],
)
def test_master_uri(
    argv: ArgvType, environ: EnvType, expected: str, mocker: MockerFixture
) -> None:
    mocker.patch.object(os, "environ", environ)
    mocker.patch.object(sys, "argv", argv)
    assert get_master_uri() == expected


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        ([], None),
        (["__name:="], None),
        (["__name:=a"], "a"),
        (["__name:=foo_bar"], "foo_bar"),
    ],
)
def test_remapped_name(argv: ArgvType, expected: str, mocker: MockerFixture) -> None:
    mocker.patch.object(sys, "argv", argv)
    assert get_remapped_name() == expected


@pytest.mark.parametrize(
    ("argv", "environ", "expected"),
    [
        ([], {}, "/"),
        (["__ns:=foo", "__ns:=bar"], {}, "foo"),
        (["__ns:=foo"], {"ROS_NAMESPACE": "bar"}, "foo"),
        ([], {"ROS_NAMESPACE": "bar"}, "bar"),
    ],
)
def test_namespace(
    argv: ArgvType, environ: EnvType, expected: str, mocker: MockerFixture
) -> None:
    mocker.patch.object(os, "environ", environ)
    mocker.patch.object(sys, "argv", argv)
    assert get_namespace() == expected


@pytest.mark.parametrize(
    ("argv", "environ", "expected"),
    [
        ([], {}, "0.0.0.0"),
        ([], {"ROS_IPV6": "on"}, "::"),
        ([], {"ROS_IPV6": "something"}, "0.0.0.0"),
        ([], {"ROS_HOSTNAME": "foo"}, "foo"),
        ([], {"ROS_IP": "127.0.0.1"}, "127.0.0.1"),
        ([], {"ROS_HOSTNAME": "foo", "ROS_IP": "127.0.0.1"}, "foo"),
        (["__ip:="], {}, "0.0.0.0"),
        (["__hostname:="], {}, "0.0.0.0"),
        (["__ip:=127.0.0.1"], {}, "127.0.0.1"),
        (["__hostname:=foo"], {}, "foo"),
        (["__ip:=127.0.0.1"], {"ROS_HOSTNAME": "foo", "ROS_IP": "bar"}, "127.0.0.1"),
        (["__hostname:=foo"], {"ROS_HOSTNAME": "foo", "ROS_IP": "bar"}, "foo"),
        (["__ip:=127.0.0.1", "__hostname:=foo"], {}, "127.0.0.1"),
        (["__hostname:=foo", "__ip:=127.0.0.1"], {}, "foo"),
    ],
)
def test_local_address(
    argv: ArgvType, environ: EnvType, expected: str, mocker: MockerFixture
) -> None:
    mocker.patch.object(os, "environ", environ)
    mocker.patch.object(sys, "argv", argv)
    assert get_local_address() == expected


def test_namespace_validation() -> None:
    assert not validate_namespace("")
    assert not validate_namespace("//")
    assert not validate_namespace("/foo//bar")
    assert not validate_namespace("/1foo")
    assert not validate_namespace("/1foo/")
    assert not validate_namespace("/foo")
    assert not validate_namespace("a")
    assert validate_namespace("/")
    assert validate_namespace("/foo/")
    assert validate_namespace("/foo1/")
    assert validate_namespace("/foo1/bar/x1/")


def test_normalize_namespace() -> None:
    assert normalize_namespace("") == "/"
    assert normalize_namespace("a") == "/a/"
    assert normalize_namespace("a/b") == "/a/b/"
    assert validate_namespace(normalize_namespace("/foo"))
    assert validate_namespace(normalize_namespace("/foo1"))
    assert validate_namespace(normalize_namespace("/foo1/bar/x1"))


@pytest.mark.parametrize(
    ("name", "node_name", "namespace", "expected"),
    [
        ("", "", "/", "/"),
        ("", "foo", "/bar", "/bar"),
        ("~", "foo", "/", "/foo"),
        ("~", "foo", "/bar", "/bar/foo"),
        ("~xy", "foo", "/", "/foo/xy"),
        ("~xy", "foo", "/bar", "/bar/foo/xy"),
        ("~xy/z", "foo", "/", "/foo/xy/z"),
        ("~xy/z", "foo", "/bar", "/bar/foo/xy/z"),
        ("~xy/z/", "foo", "/", "/foo/xy/z"),
        ("~xy/z/", "foo", "/bar", "/bar/foo/xy/z"),
        ("/xy", "foo", "/", "/xy"),
        ("/xy", "foo", "/bar", "/xy"),
    ],
)
def test_resolve_name(name: str, node_name: str, namespace: str, expected: str) -> None:
    assert resolve_name(name, node_name, namespace) == expected


@pytest.mark.parametrize(
    "name",
    ["~~", "~1", "/1", "/@", "@", "a-", "-", "~/fsdo/~"],
)
def test_invalid_names(name: str) -> None:
    pytest.raises(ValueError, resolve_name, name, "test", "/")
