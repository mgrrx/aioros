from asyncio.base_events import Server
try:
    from contextlib import asynccontextmanager
    ASYNC_CONTEXT_MANAGER = True
except ImportError:
    ASYNC_CONTEXT_MANAGER = False
from typing import Any
from typing import Callable
from typing import List
from typing import Optional
from typing import Tuple

from aiohttp.web import AppRunner

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
from .tcpros.service import Service
from .tcpros.subscription import Subscription
from .topic_manager import MsgType
from .topic_manager import TopicManager


class NodeHandle:

    def __init__(self, node_name: str) -> None:
        self._graph_resource: GraphResource = GraphResource(node_name)
        self._tcpros_uri: Optional[str] = None
        self._xmlrpc_uri: Optional[str] = None
        self._master_api_client: Optional[MasterApiClient] = None
        self._service_manager: Optional[ServiceManager] = None
        self._topic_manager: Optional[TopicManager] = None
        self._param_manager: Optional[ParamManager] = None
        self._tcpros_server: Optional[Server] = None
        self._api_server: Optional[AppRunner] = None

    @property
    def node_name(self) -> str:
        return self._graph_resource.node_name

    @property
    def namespace(self) -> str:
        return self._graph_resource.namespace

    @property
    def tcpros_uri(self) -> Optional[str]:
        return self._tcpros_uri

    @property
    def xmlrpc_uri(self) -> Optional[str]:
        return self._xmlrpc_uri

    def resolve_name(self, name: str) -> str:
        return self._graph_resource.resolve(name)

    if ASYNC_CONTEXT_MANAGER:
        @asynccontextmanager
        async def spin(
            self,
            *,
            xmlrpc_port: int = 0,
            tcpros_port: int = 0
        ) -> None:
            await self.init(xmlrpc_port=xmlrpc_port, tcpros_port=tcpros_port)
            try:
                yield self
            finally:
                await self.close()

    async def init(
        self,
        *,
        xmlrpc_port: int = 0,
        tcpros_port: int = 0
    ) -> None:
        local_address = get_local_address()
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
        self._api_server, self._xmlrpc_uri = await start_node_api_server(
            self._topic_manager,
            self._param_manager,
            self.node_name,
            self._master_api_client.uri,
            self._tcpros_uri,
            local_address,
            xmlrpc_port)
        self._master_api_client.tcpros_uri = self._tcpros_uri
        self._master_api_client.xmlrpc_uri = self._xmlrpc_uri

    async def close(self) -> None:
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

        if self._master_api_client:
            await self._master_api_client.close()
            self._master_api_client = None

        if self._api_server:
            await self._api_server.cleanup()
            self._api_server = None

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

    async def subscribe_param(
        self,
        key: str,
        callback: Callable[[str, Any], None]
    ) -> Tuple[Any, Callback]:
        return await self._param_manager.subscribe_param(key, callback)

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
