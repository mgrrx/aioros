from abc import ABC
from typing import Optional, Type

import anyio
from anyio.abc import SocketStream
from anyio.streams.buffered import BufferedByteReceiveStream

from ... import abc
from .._api import MasterApiClient
from ._protocol import (
    Serializer,
    encode_header,
    read_byte,
    read_data,
    read_error,
    read_header,
)
from ._utils import split_tcpros_uri


class ServiceClientError(Exception):
    pass


class ServiceClientInitError(ServiceClientError):
    pass


class ServiceClient(abc.ServiceClient[abc.ServiceRequestT, abc.ServiceResponseT], ABC):
    def __init__(
        self,
        service_name: str,
        service_type: Type[abc.Service[abc.ServiceRequestT, abc.ServiceResponseT]],
        master: MasterApiClient,
        node_name: str,
    ):
        self._service_name = service_name
        self._service_type = service_type
        self._master = master
        self._serializer: Serializer[abc.ServiceRequestT] = Serializer()
        self._header: abc.Header = dict(
            callerid=node_name,
            md5sum=getattr(service_type, "_md5sum"),
            service=service_name,
        )
        self._lock = anyio.Lock()

    @property
    def service_type(
        self,
    ) -> Type[abc.Service[abc.ServiceRequestT, abc.ServiceResponseT]]:
        return self._service_type

    @property
    def service_name(self) -> str:
        return self._service_name

    async def _get_client_stream(self) -> SocketStream:
        tcpros_uri = await self._master.lookup_service(self._service_name)
        client_stream = await anyio.connect_tcp(*split_tcpros_uri(tcpros_uri))

        buffered_receiver = BufferedByteReceiveStream(client_stream)
        await client_stream.send(encode_header(self._header))
        header_dict = await read_header(buffered_receiver)
        if "error" in header_dict:
            raise ServiceClientInitError(header_dict["error"]) from None

        return client_stream

    async def _call(
        self, client_stream: SocketStream, request: abc.ServiceRequestT
    ) -> abc.ServiceResponseT:
        buffered_receiver = BufferedByteReceiveStream(client_stream)

        data = await anyio.to_thread.run_sync(self._serializer.serialize, request)
        await client_stream.send(data)

        if not await read_byte(buffered_receiver):
            error = await read_error(buffered_receiver)
            raise ServiceClientError(error) from None

        data = await read_data(buffered_receiver)

        msg = self.response_class()
        await anyio.to_thread.run_sync(msg.deserialize, data)
        return msg


class NonPersistentServiceClient(ServiceClient):
    async def aclose(self) -> None:
        pass

    async def call(self, request: abc.ServiceRequestT) -> abc.ServiceResponseT:
        async with self._lock:
            async with await self._get_client_stream() as client_stream:
                return await self._call(client_stream, request)


class PersistentServiceClient(ServiceClient):
    def __init__(
        self,
        service_name: str,
        service_type: Type[abc.Service[abc.ServiceRequestT, abc.ServiceResponseT]],
        master: MasterApiClient,
        node_name: str,
    ):
        super().__init__(service_name, service_type, master, node_name)
        self._header["persistent"] = "1"
        self._client_stream: Optional[SocketStream] = None

    async def aclose(self) -> None:
        async with self._lock:
            if self._client_stream:
                await self._client_stream.aclose()
                self._client_stream = None

    async def call(self, request: abc.ServiceRequestT) -> abc.ServiceResponseT:
        async with self._lock:
            return await self._call(await self._get_client_stream(), request)

    async def _get_client_stream(self) -> SocketStream:
        if self._client_stream is None:
            self._client_stream = await super()._get_client_stream()
        return self._client_stream
