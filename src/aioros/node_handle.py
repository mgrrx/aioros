from asyncio import get_event_loop
from asyncio.base_events import Server
from os import getuid
from pathlib import Path
from typing import Any
from typing import Callable
from typing import List
from typing import Optional
from typing import Tuple

from aiohttp.web import AppRunner

from genpy import Time

from .api.master_api_client import MasterApiClient
from .api.node_api_server import start_server as start_node_api_server
from .graph_resource import GraphResource
from .graph_resource import get_local_address
from .graph_resource import get_master_uri
from .param_manager import Callback
from .param_manager import ParamManager
from .service_manager import ServiceManager
from .service_manager import SrvType
from .service_manager import SrvTypeRequest
from .service_manager import SrvTypeResponse
from .tcpros.client import Client
from .tcpros.publisher import Publisher
from .tcpros.server import start_server as start_tcpros_server
from .tcpros.server import start_unix_server as start_unixros_server
from .tcpros.service import Service
from .tcpros.subscription import Subscription
from .time_manager import start_time_manager
from .time_manager import TimeManager
from .topic_manager import MsgType
from .topic_manager import TopicManager


class NodeHandle:

    def __init__(self, node_name: str) -> None:
        self._graph_resource: GraphResource = GraphResource(node_name)
        self._tcpros_uri: Optional[str] = None
        self._xmlrpc_uri: Optional[str] = None
        self._unixros_uri: Optional[str] = None
        self._master_api_client: Optional[MasterApiClient] = None
        self._service_manager: Optional[ServiceManager] = None
        self._topic_manager: Optional[TopicManager] = None
        self._param_manager: Optional[ParamManager] = None
        self._tcpros_server: Optional[Server] = None
        self._unixros_server: Optional[Server] = None
        self._api_server: Optional[AppRunner] = None
        self._time_manager: Optional[TimeManager] = None

    @property
    def node_name(self) -> str:
        return self._graph_resource.node_name

    @property
    def namespace(self) -> str:
        return self._graph_resource.namespace

    def resolve_name(self, name: str) -> str:
        return self._graph_resource.resolve(name)

    async def init(
        self,
        *,
        xmlrpc_port: int = 0,
        tcpros_port: int = 0,
        unixros_path: Path = None,
    ) -> None:
        local_address = get_local_address()
        unixros_path = \
            unixros_path or \
            (Path('/run/user') / str(getuid()) / self.node_name[1:])
        if not unixros_path.parent.exists():
            unixros_path.parent.mkdir()

        self._master_api_client = MasterApiClient(
            self.node_name,
            get_master_uri())
        self._service_manager = ServiceManager(self._master_api_client)
        self._topic_manager = TopicManager(self._master_api_client)
        self._param_manager = ParamManager(self._master_api_client)
        self._tcpros_server, self._tcpros_uri = await start_tcpros_server(
            self._service_manager,
            self._topic_manager,
            local_address,
            tcpros_port)
        self._unixros_server, self._unixros_uri = await start_unixros_server(
            self._service_manager,
            self._topic_manager,
            unixros_path)
        self._api_server, self._xmlrpc_uri = await start_node_api_server(
            self._topic_manager,
            self._param_manager,
            self.node_name,
            self._master_api_client.uri,
            self._tcpros_uri,
            self._unixros_uri,
            local_address,
            xmlrpc_port)
        self._time_manager = await start_time_manager(self)
        self._master_api_client.tcpros_uri = self._tcpros_uri
        self._master_api_client.unixros_uri = self._unixros_uri
        self._master_api_client.xmlrpc_uri = self._xmlrpc_uri

    async def close(self) -> None:
        if self._time_manager:
            await self._time_manager.close()
            self._time_manager = None

        if self._service_manager:
            await self._service_manager.close()
            self._service_manager = None

        if self._topic_manager:
            await self._topic_manager.close()
            self._topic_manager = None

        if self._param_manager:
            self._param_manager = None

        if self._tcpros_server:
            self._tcpros_server.close()
            await self._tcpros_server.wait_closed()
            self._tcpros_server = None

        if self._unixros_server:
            self._unixros_server.close()
            await self._unixros_server.wait_closed()
            self._unixros_server = None

        if self._master_api_client:
            await self._master_api_client.close()
            self._master_api_client = None

        if self._api_server:
            await self._api_server.cleanup()
            self._api_server = None

        self._tcpros_uri = None
        self._xmlrpc_uri = None
        self._unixros_uri = None

    async def delete_param(self, key: str) -> None:
        return await self._master_api_client.delete_param(
            self.resolve_name(key))

    async def set_param(self, key: str, value: Any) -> None:
        return await self._master_api_client.set_param(
            self.resolve_name(key),
            value)

    async def get_param(self, key: str) -> Any:
        return await self._master_api_client.get_param(
            self.resolve_name(key))

    async def has_param(self, key: str) -> bool:
        return await self._master_api_client.has_param(
            self.resolve_name(key))

    async def search_param(self, key: str) -> Any:
        return await self._master_api_client.search_param(
            self.resolve_name(key))

    async def get_param_names(self) -> List[str]:
        return await self._master_api_client.get_param_names()

    async def lookup_service(self, service: str) -> str:
        return await self._master_api_client.lookup_service(
            self.resolve_name(service))

    async def subscribe_param(
        self,
        key: str,
        callback: Callable[[str, Any], None]
    ) -> Tuple[Any, Callback]:
        return await self._param_manager.subscribe_param(
            self.resolve_name(key),
            callback)

    async def unsubscribe_param_callback(
        self,
        callback: Callback
    ) -> bool:
        return await self._param_manager.unsubscribe_callback(callback)

    async def create_subscription(
        self,
        topic_name: str,
        msg_type: MsgType,
        callback: Callable[[MsgType], None]
    ) -> Subscription:
        return await self._topic_manager.create_subscription(
            self.node_name,
            self.resolve_name(topic_name),
            msg_type,
            callback)

    async def create_publisher(
        self,
        topic_name: str,
        msg_type: MsgType,
        *,
        on_peer_connect: Optional[Callable] = None,
        on_peer_disconnect: Optional[Callable] = None,
        latch: bool = False
    ) -> Publisher:
        return await self._topic_manager.create_publisher(
            self.node_name,
            self.resolve_name(topic_name),
            msg_type,
            on_peer_connect=on_peer_connect,
            on_peer_disconnect=on_peer_disconnect,
            latch=latch)

    async def create_service(
        self,
        srv_name: str,
        srv_type: SrvType,
        callback: Callable[[SrvTypeRequest], SrvTypeResponse]
    ) -> Service:
        return await self._service_manager.create_service(
            self.node_name,
            self.resolve_name(srv_name),
            srv_type,
            callback)

    async def create_client(
        self,
        srv_name: str,
        srv_type: SrvType,
        *,
        persistent: bool = False
    ) -> Client:
        return await self._service_manager.create_client(
            self.node_name,
            self.resolve_name(srv_name),
            srv_type,
            persistent=persistent)

    def get_time(self) -> Time:
        return self._time_manager.get_time()


def run_until_complete(
    func: Callable[[NodeHandle], int],
    node_name: str,
    *,
    loop=None,
    xmlrpc_port: int = 0,
    tcpros_port: int = 0
) -> int:
    node_handle = NodeHandle(node_name)
    loop = loop or get_event_loop()
    try:
        loop.run_until_complete(node_handle.init(
            xmlrpc_port=xmlrpc_port,
            tcpros_port=tcpros_port))
        return_value = loop.run_until_complete(func(node_handle))
    except KeyboardInterrupt as e:
        loop.run_until_complete(node_handle.close())
        loop.stop()
        loop.run_until_complete(loop.shutdown_asyncgens())
        return -1
    else:
        loop.run_until_complete(node_handle.close())
    return return_value


def run_forever(
    func: Callable[[NodeHandle], int],
    node_name: str,
    *,
    loop=None,
    xmlrpc_port: int = 0,
    tcpros_port: int = 0
) -> None:
    node_handle = NodeHandle(node_name)
    loop = loop or get_event_loop()
    try:
        loop.run_until_complete(node_handle.init(
            xmlrpc_port=xmlrpc_port,
            tcpros_port=tcpros_port))
        loop.run_until_complete(func(node_handle))
        loop.run_forever()
    except KeyboardInterrupt as e:
        print("Received KeyboardInterrupt, shutting down...")
        loop.run_until_complete(node_handle.close())
        loop.stop()
        loop.run_until_complete(loop.shutdown_asyncgens())
    else:
        loop.run_until_complete(node_handle.close())
