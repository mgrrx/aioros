from typing import cast
from xmlrpc.client import Server

import anyio
import pytest
from std_srvs.srv import SetBool, SetBoolRequest, SetBoolResponse

from aioros import init_node
from aioros._node._node import Node
from aioros.master import init_master
from anyio_xmlrpc.client import ServerProxy

pytestmark = pytest.mark.anyio


async def service_cb(request: SetBoolRequest) -> SetBoolResponse:
    return SetBoolResponse(message=str(request.data), success=True)


async def wait_until_registered(uri: str) -> None:
    async with ServerProxy(uri) as server_proxy:
        while True:
            code, _, _ = await server_proxy.lookupService("test", "/set_bool")
            if code == 1:
                break
            await anyio.sleep(0.01)


async def test_service() -> None:
    async with init_master() as master:
        async with cast(
            Node,
            init_node(
                "some_server",
                master_uri=master.xmlrpc_uri,
                register_signal_handler=False,
                configure_logging=False,
            ),
        ) as server:
            async with anyio.create_task_group() as task_group:

                task_group.start_soon(
                    server.create_server("/set_bool", SetBool, service_cb).serve
                )

                async with init_node(
                    "test_client",
                    master_uri=master.xmlrpc_uri,
                    register_signal_handler=False,
                    configure_logging=False,
                ) as node:
                    await wait_until_registered(master.xmlrpc_uri)
                    assert (
                        master.registry.services["/set_bool"].api == server.tcpros_uri
                    )
                    async with node.create_client("/set_bool", SetBool) as client:
                        for _ in range(10):
                            result = await client.call(SetBoolRequest(True))
                            print(result)
                            assert result.success is True
                            assert result.message == "True"

                    async with node.create_client(
                        "/set_bool", SetBool, persistent=True
                    ) as client:
                        for _ in range(10):
                            result = await client.call(SetBoolRequest(True))
                            print(result)
                            assert result.success is True
                            assert result.message == "True"
                task_group.cancel_scope.cancel()

        assert "/set_bool" not in master.registry.services
        assert not master.registry.nodes
        assert not master.registry.services
