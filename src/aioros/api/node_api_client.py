from functools import partial
from typing import Any
from typing import List

from aiohttp_xmlrpc.client import ServerProxy

from .utils import validate
from .utils import validate_with_keyerror


class NodeApiClientError(Exception):
    pass


validate = partial(validate, NodeApiClientError)
validate_with_keyerror = partial(validate_with_keyerror, NodeApiClientError)


class NodeApiClient:

    def __init__(
        self,
        own_node_name: str,
        node_uri: str
    ) -> None:
        self._own_node_name = own_node_name
        self._proxy = ServerProxy(node_uri)

    @property
    def uri(self) -> str:
        return self._proxy.url

    async def close(self) -> None:
        await self._proxy.close()

    @validate()
    async def request_topic(
        self,
        resolved_topic: str,
        protocols: List[str]
    ) -> List[Any]:
        return await self._proxy.requestTopic(
            self._own_node_name,
            resolved_topic,
            protocols)
