from asyncio import Lock
from functools import partial
from sys import maxsize as _MAX_SIZE
from typing import Any
from typing import Optional
from typing import List
from typing import Tuple

from aiohttp import ClientSession
from aiohttp import TCPConnector
from aiohttp_xmlrpc.client import ServerProxy

from .utils import validate
from .utils import validate_with_keyerror


class MasterApiClientError(Exception):
    pass


validate = partial(validate, MasterApiClientError)
validate_with_keyerror = partial(validate_with_keyerror, MasterApiClientError)


class MasterApiClient:

    def __init__(
        self,
        node_name: str,
        master_uri: str,
        *,
        xmlrpc_uri: Optional[str] = None,
        tcpros_uri: Optional[str] = None,
        unixros_uri: Optional[str] = None
    ) -> None:
        self._node_name = node_name
        self.xmlrpc_uri = xmlrpc_uri
        self.tcpros_uri = tcpros_uri
        self.unixros_uri = unixros_uri
        self._proxy: ServerProxy = ServerProxy(
            master_uri,
            client=ClientSession(
                connector=TCPConnector(keepalive_timeout=_MAX_SIZE)))
        self._lock: Lock = Lock()

    @property
    def uri(self) -> str:
        return self._proxy.url

    async def close(self) -> None:
        await self._proxy.close()

    @validate_with_keyerror(return_value=False)
    async def delete_param(self, key: str) -> None:
        async with self._lock:
            return await self._proxy.deleteParam(self._node_name, key)

    @validate_with_keyerror(return_value=False)
    async def set_param(self, key: str, value: Any) -> None:
        async with self._lock:
            return await self._proxy.setParam(self._node_name, key, value)

    @validate_with_keyerror()
    async def get_param(self, key: str):
        async with self._lock:
            return await self._proxy.getParam(self._node_name, key)

    @validate_with_keyerror()
    async def has_param(self, key: str) -> bool:
        async with self._lock:
            return await self._proxy.hasParam(self._node_name, key)

    @validate_with_keyerror()
    async def search_param(self, key: str):
        async with self._lock:
            return await self._proxy.searchParam(self._node_name, key)

    @validate()
    async def get_param_names(self) -> List[str]:
        async with self._lock:
            return await self._proxy.getParamNames(self._node_name)

    @validate()
    async def subscribe_param(self, key):
        async with self._lock:
            return await self._proxy.subscribeParam(
                self._node_name,
                self.xmlrpc_uri,
                key)

    @validate()
    async def unsubscribe_param(self, key):
        async with self._lock:
            return await self._proxy.unsubscribeParam(
                self._node_name,
                self.xmlrpc_uri,
                key)

    @validate()
    async def lookup_node(self, node_name: str) -> str:
        async with self._lock:
            return await self._proxy.lookupNode(self._node_name, node_name)

    @validate()
    async def lookup_service(self, service: str) -> str:
        async with self._lock:
            return await self._proxy.lookupService(self._node_name, service)

    @validate()
    async def get_published_topics(
        self,
        subgraph: str = ''
    ) -> List[Tuple[str, str]]:
        async with self._lock:
            return await self._proxy.getPublishedTopics(
                self._node_name,
                subgraph)

    @validate(return_value=False)
    async def register_service(self, service: str) -> None:
        async with self._lock:
            return await self._proxy.registerService(
                self._node_name,
                service,
                self.tcpros_uri,
                self.xmlrpc_uri)

    @validate()
    async def unregister_service(self, service: str) -> int:
        async with self._lock:
            return await self._proxy.unregisterService(
                self._node_name,
                service,
                self.tcpros_uri)

    @validate()
    async def register_subscriber(
        self,
        topic: str,
        topic_type: str
    ) -> List[str]:
        async with self._lock:
            return await self._proxy.registerSubscriber(
                self._node_name,
                topic,
                topic_type,
                self.xmlrpc_uri)

    @validate()
    async def unregister_subscriber(
        self,
        topic: str,
        topic_type: str
    ) -> int:
        async with self._lock:
            return await self._proxy.unregisterSubscriber(
                self._node_name,
                topic,
                self.xmlrpc_uri)

    @validate()
    async def register_publisher(
        self,
        topic: str,
        topic_type: str
    ) -> List[str]:
        async with self._lock:
            return await self._proxy.registerPublisher(
                self._node_name,
                topic,
                topic_type,
                self.xmlrpc_uri)

    @validate()
    async def unregister_publisher(
        self,
        topic: str,
        topic_type: str
    ) -> int:
        async with self._lock:
            return await self._proxy.unregisterPublisher(
                self._node_name,
                topic,
                self.xmlrpc_uri)
