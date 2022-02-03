from functools import partial
from typing import Awaitable, Callable, Dict, Iterable, TypeVar

import httpx
from anyio.abc import AsyncResource

from ._protocol._client import build_xml, parse_xml
from ._protocol._common import XmlRpcTypes

ServerProxyT = TypeVar("ServerProxyT", bound="ServerProxy")


class ServerProxy(AsyncResource):
    __slots__ = "url", "_huge_tree", "_session"

    def __init__(
        self, url: str, *, headers: Dict[bytes, bytes] = None, huge_tree: bool = False
    ) -> None:
        headers = headers or {}
        headers.setdefault(b"Content-Type", b"text/xml")
        self.url = url
        self.headers = headers

        self._huge_tree = huge_tree
        self._client = httpx.AsyncClient()

    def __getattr__(
        self, method_name: str
    ) -> Callable[[Iterable[XmlRpcTypes]], Awaitable[XmlRpcTypes]]:
        return self[method_name]

    def __getitem__(
        self, method_name: str
    ) -> Callable[[Iterable[XmlRpcTypes]], Awaitable[XmlRpcTypes]]:
        return partial(self.__remote_call, method_name)

    async def __remote_call(
        self, method_name: str, *args: Iterable[XmlRpcTypes]
    ) -> XmlRpcTypes:
        response = await self._client.post(
            self.url,
            content=build_xml(method_name, *args),
            headers=self.headers,
        )
        assert response.status_code == 200

        return parse_xml(response.content, method_name, huge_tree=self._huge_tree)

    async def __aenter__(self: ServerProxyT) -> ServerProxyT:
        await self._client.__aenter__()
        return self

    async def aclose(self) -> None:
        await self._client.aclose()
