from asyncio import IncompleteReadError
from asyncio import StreamReader
from asyncio import StreamWriter
from asyncio import open_connection
from typing import Dict
from typing import Optional
from typing import Tuple
from typing import TypeVar

from .protocol import Serializer
from .protocol import encode_header
from .protocol import read_byte
from .protocol import read_data
from .protocol import read_error
from .protocol import read_header
from .utils import split_tcpros_uri


class ClientInitError(Exception):
    pass


class ServiceError(Exception):
    pass


SrvType = TypeVar('SrvType')
SrvTypeRequest = TypeVar('SrvTypeRequest')
SrvTypeResponse = TypeVar('SrvTypeResponse')
ReaderWriter = Tuple[StreamReader, StreamWriter]


class Client:

    def __init__(
        self,
        node_name: str,
        srv_name: str,
        srv_type: SrvType,
        tcpros_uri: str
    ) -> None:
        self._srv_name: str = srv_name
        self._srv_type: SrvType = srv_type
        self._host, self._port = split_tcpros_uri(tcpros_uri)
        self._serializer: Serializer = Serializer()
        self._header: Dict[str, str] = dict(
            callerid=node_name,
            md5sum=self.md5sum,
            service=self.name,
        )

    @property
    def name(self) -> str:
        return self._srv_name

    @property
    def type(self):
        return self._srv_type

    @property
    def type_name(self) -> str:
        return self._srv_type._type

    @property
    def md5sum(self) -> str:
        return self._srv_type._md5sum

    @property
    def header(self) -> Dict[str, str]:
        return self._header

    async def call(self, request: SrvTypeRequest) -> SrvTypeResponse:
        try:
            reader, writer = await self._get_connection()
            return await self._call(request, reader, writer)
        except (IncompleteReadError, ConnectionResetError) as err:
            await self.close()
            raise ServiceError()

    async def _call(
        self,
        request: SrvTypeRequest,
        reader: StreamReader,
        writer: StreamWriter
    ) -> SrvTypeResponse:
        await self._initialize(reader, writer)

        with self._serializer.serialize(request) as data:
            writer.write(data)
        await writer.drain()

        ok = await read_byte(reader)
        if not ok:
            error = await read_error(reader)
            raise ServiceError(error)

        data = await read_data(reader)

        msg = self._srv_type._response_class()
        msg.deserialize(data)
        return msg

    async def _get_connection(self) -> ReaderWriter:
        return await open_connection(self._host, self._port)

    async def _initialize(
        self,
        reader: StreamReader,
        writer: StreamWriter
    ) -> None:
        writer.write(encode_header(self.header))
        await writer.drain()

        header_dict = await read_header(reader)
        if 'error' in header_dict:
            raise ClientInitError(header_dict['error'])

    async def close(self) -> None:
        pass


class NonPersistentClient(Client):

    async def _call(
        self,
        request: SrvTypeRequest,
        reader: StreamReader,
        writer: StreamWriter
    ) -> SrvTypeResponse:
        msg: SrvTypeResponse = await super()._call(request, reader, writer)
        writer.close()
        if hasattr(writer, 'wait_closed'):
            await writer.wait_closed()
        return msg


class PersistentClient(Client):

    def __init__(
        self,
        node_name: str,
        srv_name: str,
        srv_type: SrvType,
        tcpros_uri: str
    ) -> None:
        super().__init__(node_name, srv_name, srv_type, tcpros_uri)
        self._initialized: bool = False
        self._reader_writer: Optional[ReaderWriter] = None

    @property
    def header(self) -> Dict[str, str]:
        return dict(super().header, persistent='1')

    async def _get_connection(self) -> ReaderWriter:
        if not self._reader_writer:
            self._reader_writer = await super()._get_connection()
        return self._reader_writer

    async def _initialize(
        self,
        reader: StreamReader,
        writer: StreamWriter
    ) -> None:
        if self._initialized:
            return
        await super()._initialize(reader, writer)
        self._initialized = True

    async def close(self) -> None:
        if self._reader_writer:
            writer = self._reader_writer[1]
            writer.close()
            if hasattr(writer, 'wait_closed'):
                await writer.wait_closed()
            self._reader_writer = None


def create_client(
    node_name: str,
    srv_name: str,
    srv_type: SrvType,
    tcpros_uri: str,
    persistent: bool = False
) -> Client:
    client_cls = PersistentClient if persistent else NonPersistentClient
    return client_cls(node_name, srv_name, srv_type, tcpros_uri)
