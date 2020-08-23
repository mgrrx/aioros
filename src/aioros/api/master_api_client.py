from asyncio import Lock
from functools import partial
from sys import maxsize as _MAX_SIZE
from typing import Any
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
        node_handle,
        master_uri: str
    ) -> None:
        self._node_handle = node_handle
        self._proxy = ServerProxy(
            master_uri,
            client=ClientSession(
                connector=TCPConnector(keepalive_timeout=_MAX_SIZE)))
        self._lock = Lock()

    @property
    def uri(self) -> str:
        return self._proxy.url

    async def close(self) -> None:
        await self._proxy.close()

    @validate_with_keyerror(return_value=False)
    async def delete_param(self, key: str) -> None:
        async with self._lock:
            return await self._proxy.deleteParam(
                self._node_handle.node_name,
                self._node_handle.resolve_name(key))

    @validate_with_keyerror(return_value=False)
    async def set_param(self, key: str, value: Any) -> None:
        async with self._lock:
            return await self._proxy.setParam(
                self._node_handle.node_name,
                self._node_handle.resolve_name(key),
                value)

    @validate_with_keyerror()
    async def get_param(self, key: str):
        async with self._lock:
            return await self._proxy.getParam(
                self._node_handle.node_name,
                self._node_handle.resolve_name(key))

    @validate_with_keyerror()
    async def has_param(self, key: str) -> bool:
        async with self._lock:
            return await self._proxy.hasParam(
                self._node_handle.node_name,
                self._node_handle.resolve_name(key))

    @validate_with_keyerror()
    async def search_param(self, key: str):
        async with self._lock:
            return await self._proxy.searchParam(
                self._node_handle.node_name,
                self._node_handle.resolve_name(key))

    @validate()
    async def get_param_names(self) -> List[str]:
        async with self._lock:
            return await self._proxy.getParamNames(
                self._node_handle.node_name)

    async def subscribe_param(self, key):
        raise NotImplementedError()

    async def unsubscribe_param(self, key):
        raise NotImplementedError()

    @validate()
    async def lookup_node(self, node_name: str) -> str:
        async with self._lock:
            return await self._proxy.lookupNode(
                self._node_handle.node_name,
                node_name)

    @validate()
    async def lookup_service(self, service: str) -> str:
        async with self._lock:
            return await self._proxy.lookupService(
                self._node_handle.node_name,
                self._node_handle.resolve_name(service))

    @validate()
    async def get_published_topics(
        self,
        subgraph: str = ''
    ) -> List[Tuple[str, str]]:
        async with self._lock:
            return await self._proxy.getPublishedTopics(
                self._node_handle.node_name,
                self._node_handle.resolve_name(subgraph))

    @validate(return_value=False)
    async def register_service(self, service: str) -> None:
        async with self._lock:
            return await self._proxy.registerService(
                self._node_handle.node_name,
                self._node_handle.resolve_name(service),
                self._node_handle.tcpros_uri,
                self._node_handle.xmlrpc_uri)

    @validate()
    async def unregister_service(self, service: str) -> int:
        async with self._lock:
            return await self._proxy.unregisterService(
                self._node_handle.node_name,
                self._node_handle.resolve_name(service),
                self._node_handle.tcpros_uri)

    @validate()
    async def register_subscriber(
        self,
        topic: str,
        topic_type: str
    ) -> List[str]:
        async with self._lock:
            return await self._proxy.registerSubscriber(
                self._node_handle.node_name,
                self._node_handle.resolve_name(topic),
                topic_type,
                self._node_handle.xmlrpc_uri)

    @validate()
    async def unregister_subscriber(
        self,
        topic: str,
        topic_type: str
    ) -> int:
        async with self._lock:
            return await self._proxy.unregisterSubscriber(
                self._node_handle.node_name,
                self._node_handle.resolve_name(topic),
                self._node_handle.xmlrpc_uri)

    @validate()
    async def register_publisher(
        self,
        topic: str,
        topic_type: str
    ) -> List[str]:
        async with self._lock:
            return await self._proxy.registerPublisher(
                self._node_handle.node_name,
                self._node_handle.resolve_name(topic),
                topic_type,
                self._node_handle.xmlrpc_uri)

    @validate()
    async def unregister_publisher(
        self,
        topic: str,
        topic_type: str
    ) -> int:
        async with self._lock:
            return await self._proxy.unregisterPublisher(
                self._node_handle.node_name,
                self._node_handle.resolve_name(topic),
                self._node_handle.xmlrpc_uri)
