from contextlib import asynccontextmanager
from dataclasses import dataclass

import pytest
from anyio.abc import AsyncResource

from aioros import init_node
from aioros.abc import Node
from aioros.master import Master, init_master

pytestmark = pytest.mark.anyio


@dataclass
class MasterNode(AsyncResource):
    master: Master
    node: Node

    async def aclose(self) -> None:
        pass


@asynccontextmanager
async def create_master_node():
    async with init_master() as master:
        async with init_node(
            "test_node",
            master_uri=master.xmlrpc_uri,
            register_signal_handler=False,
            configure_logging=False,
        ) as node:
            yield MasterNode(master, node)


async def test_master() -> None:
    async with create_master_node() as master_node:
        assert await master_node.node.get_param_names() == []
        await master_node.node.set_param("/foo", 1)
        assert await master_node.node.get_param("/foo") == 1

        await master_node.node.set_param("bar", 2)
        assert await master_node.node.get_param("bar") == 2
        assert await master_node.node.get_param("/bar") == 2
        assert set(await master_node.node.get_param_names()) == {"/foo", "/bar"}
        assert set(master_node.master.param_cache.keys()) == {"/foo", "/bar"}

        await master_node.node.set_param("~foobar", 3)
        assert await master_node.node.get_param("~foobar") == 3
        assert set(await master_node.node.get_param_names()) == {
            "/foo",
            "/bar",
            "/test_node/foobar",
        }
        assert await master_node.node.get_param("/test_node/foobar") == 3
