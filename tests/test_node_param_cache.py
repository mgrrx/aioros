from typing import cast

import anyio
import pytest

from aioros import init_node
from aioros._node._node import Node
from aioros._node._param_cache import ParamCache
from aioros.master import init_master

pytestmark = pytest.mark.anyio


def test_param_cache1() -> None:
    cache = ParamCache()
    cache.add("/foo", {"bar": 1})
    assert cache["/foo/bar"] == 1
    assert cache["/foo"] == {"bar": 1}
    assert "/foo/bar" in cache
    assert "/foo" in cache
    with pytest.raises(KeyError):
        cache["/"]

    cache.update("/foo/x", 2)

    assert cache["/foo"] == {"bar": 1, "x": 2}

    cache.update("/foo/y/z", 3)

    assert cache["/foo"] == {"bar": 1, "x": 2, "y": {"z": 3}}


async def test_local_parameters() -> None:
    async with init_master() as master:
        async with init_node(
            "node",
            master_uri=master.xmlrpc_uri,
            register_signal_handler=False,
            configure_logging=False,
        ) as node:
            node = cast(Node, node)
            await node.set_param("/foo", 1)
            assert (await node.get_param("/foo")) == 1
            assert "foo" not in node._param_cache

            assert (await node.get_param_cached("/foo")) == 1
            assert "foo" in node._param_cache
            assert node._param_cache["foo"] == 1
            assert (await node.get_param("/foo")) == 1

            node._param_cache.update("foo", 2)
            assert (await node.get_param("/foo")) == 2


def notify_when_called(obj: object, function_name: str) -> anyio.Event:
    event = anyio.Event()

    method = getattr(obj, function_name)

    def wrapper(*args, **kwargs):
        method(*args, **kwargs)
        event.set()
        setattr(obj, function_name, method)

    setattr(obj, function_name, wrapper)

    return event


async def test_param_subscription() -> None:
    async with init_master() as master:
        async with init_node(
            "node1",
            master_uri=master.xmlrpc_uri,
            register_signal_handler=False,
            configure_logging=False,
        ) as node1, init_node(
            "node2",
            master_uri=master.xmlrpc_uri,
            register_signal_handler=False,
            configure_logging=False,
        ) as node2:
            node1 = cast(Node, node1)
            await node2.set_param("/foo", 1)
            assert (await node1.get_param_cached("/foo")) == 1

            event = notify_when_called(node1._param_cache, "update")
            await node2.set_param("/foo", 2)
            await event.wait()

            assert (await node1.get_param_cached("/foo")) == 2

            event = notify_when_called(node1._param_cache, "update")
            await node2.set_param("/foo", {"x": 1})
            await event.wait()

            assert (await node1.get_param_cached("/foo")) == {"x": 1}

            event = notify_when_called(node1._param_cache, "update")
            await node2.set_param("/foo/x", 3)
            await event.wait()

            assert (await node1.get_param_cached("/foo/x")) == 3
