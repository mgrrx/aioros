import logging
from typing import Awaitable, Callable, Type

import anyio
from anyio.abc import SocketStream
from anyio.streams.buffered import BufferedByteReceiveStream

from ... import abc
from .._api import MasterApiClient
from ._protocol import Serializer, encode_byte, encode_header, encode_str, read_data
from ._utils import check_md5sum, require_fields

logger = logging.getLogger(__name__)


class ServiceServer(abc.ServiceServer[abc.ServiceRequestT, abc.ServiceResponseT]):
    def __init__(
        self,
        service_name: str,
        service_type: Type[abc.Service[abc.ServiceRequestT, abc.ServiceResponseT]],
        handler: Callable[[abc.ServiceRequestT], Awaitable[abc.ServiceResponseT]],
        master: MasterApiClient,
        node_name: str,
    ) -> None:
        self._service_name = service_name
        self._service_type = service_type
        self._handler = handler
        self._master = master
        self._node_name = node_name

    @property
    def service_type(
        self,
    ) -> Type[abc.Service[abc.ServiceRequestT, abc.ServiceResponseT]]:
        return self._service_type

    @property
    def service_name(self) -> str:
        return self._service_name

    @property
    def header(self) -> abc.Header:
        return dict(
            callerid=self._node_name,
            md5sum=getattr(self.service_type, "_md5sum"),
            service=self.service_name,
            type=getattr(self.service_type, "_type"),
        )

    async def serve(self) -> None:
        await self._master.register_service(self.service_name)
        try:
            await anyio.sleep_forever()
        except anyio.get_cancelled_exc_class():
            with anyio.CancelScope(shield=True), anyio.move_on_after(1):
                await self._master.unregister_service(self.service_name)
            raise

    async def handle_tcpros(
        self,
        protocol: str,
        header: abc.Header,
        client: SocketStream,
    ) -> None:
        """Handle incoming service client traffic."""

        require_fields(header, "service", "md5sum", "callerid")

        check_md5sum(header, getattr(self.service_type, "_md5sum"))

        await client.send(encode_header(self.header))

        if header.get("probe") == "1":
            return

        persistent = header.get("persistent", "").lower() in ("1", "true")
        serializer: Serializer[abc.ServiceRequestT] = Serializer()

        buffered_receiver = BufferedByteReceiveStream(client)

        while True:
            request = self.request_class()
            data = await read_data(buffered_receiver)
            await anyio.to_thread.run_sync(request.deserialize, data)
            setattr(request, "_connection_header", header)
            try:
                result = await self._handler(request)
            except anyio.get_cancelled_exc_class():
                raise
            except Exception:  # pylint: disable=broad-except
                logger.error("Exception occured in service callback", exc_info=True)
                await client.send(
                    encode_byte(0) + encode_str("error processing request")
                )
            else:
                data = await anyio.to_thread.run_sync(serializer.serialize, result)
                await client.send(encode_byte(1) + data)

            if not persistent:
                return
