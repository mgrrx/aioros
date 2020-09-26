from asyncio import IncompleteReadError
from asyncio import Queue
from asyncio import StreamReader
from asyncio import StreamWriter
from asyncio import start_server
from asyncio import start_unix_server
from asyncio.base_events import Server
from functools import partial
from functools import wraps
from pathlib import Path
from typing import Dict
from typing import Tuple

from ..service_manager import ServiceManager
from ..topic_manager import TopicManager
from .protocol import Serializer
from .protocol import encode_byte
from .protocol import encode_header
from .protocol import encode_str
from .protocol import read_data
from .protocol import read_header


class Error(Exception):

    @property
    def msg(self) -> str:
        return self.args[0]


def handle_io_error(func):

    @wraps(func)
    async def wrapper(
        service_manager: ServiceManager,
        topic_manager: TopicManager,
        reader: StreamReader,
        writer: StreamWriter
    ) -> None:
        try:
            await func(service_manager, topic_manager, reader, writer)
        except (ConnectionResetError, IncompleteReadError):
            writer.close()

    return wrapper


@handle_io_error
async def handle(
    service_manager: ServiceManager,
    topic_manager: TopicManager,
    reader: StreamReader,
    writer: StreamWriter
) -> None:
    header = await read_header(reader)
    if 'service' in header or 'topic' in header:
        try:
            if 'service' in header:
                await handle_service(service_manager, reader, writer, header)
            else:
                await handle_topic(topic_manager, reader, writer, header)
        except Error as err:
            writer.write(encode_header(dict(error=err.msg)))
            await writer.drain()
    else:
        writer.write(
            encode_header(dict(error='no topic or service name detected')))
        await writer.drain()

    writer.close()
    if hasattr(writer, 'wait_closed'):
        await writer.wait_closed()


def require_fields(
    header: Dict[str, str],
    *fields: str
) -> None:
    for field in fields:
        if field not in header:
            raise Error(f"Missing required '{field}' field")


def check_md5sum(
    header: Dict[str, str],
    md5sum: str
) -> None:
    if header['md5sum'] not in ('*', md5sum):
        raise Error('request from [{}]: md5sums do not match: [{}] vs. [{}]'
                    ''.format(header['callerid'], header['md5sum'], md5sum))


async def handle_service(
    service_manager: ServiceManager,
    reader: StreamReader,
    writer: StreamWriter,
    header: Dict[str, str]
) -> None:
    require_fields(header, 'service', 'md5sum', 'callerid')

    service_name = header['service']
    service = service_manager.get(service_name)
    if not service:
        raise Error(f'Service {service_name} is not provided by this node')

    check_md5sum(header, service.md5sum)

    writer.write(encode_header(service.header))
    await writer.drain()

    if header.get('probe') == '1':
        return

    persistent = header.get('persistent', '').lower() in ('1', 'true')
    serializer = Serializer()

    while True:
        request = service.type._request_class()
        request.deserialize(await read_data(reader))
        request._connection_header = header
        try:
            result = service.callback(request)
        except Exception:
            writer.write(encode_byte(0))
            writer.write(encode_str('error processing request'))
        else:
            writer.write(encode_byte(1))
            with serializer.serialize(result) as data:
                writer.write(data)
        finally:
            await writer.drain()

        if not persistent:
            return


async def handle_topic(
    topic_manager: TopicManager,
    reader: StreamReader,
    writer: StreamWriter,
    header: Dict[str, str]
) -> None:
    require_fields(header, 'topic', 'md5sum', 'callerid')
    topic_name = header['topic']
    topic = topic_manager.get(topic_name)
    if not topic:
        raise Error(f'Topic {topic_name} is not provided by this node')

    try:
        check_md5sum(header, topic.md5sum)

        writer.write(encode_header(topic.get_publisher_header()))
        await writer.drain()

        queue = Queue()
        await topic.connect_subscriber(header['callerid'], queue)

        while True:
            writer.write(await queue.get())
            await writer.drain()
            queue.task_done()
    except Exception as err:
        topic.disconnect_subscriber(header['callerid'])
        raise err
    topic.disconnect_subscriber(header['callerid'])


async def start_tcpros_server(
    service_manager: ServiceManager,
    topic_manager: TopicManager,
    host: str,
    port: int
) -> Tuple[Server, str]:
    server: Server = await start_server(
        partial(handle, service_manager, topic_manager),
        host=host,
        port=port)

    return server, 'rosrpc://{}:{}'.format(*server.sockets[0].getsockname())


async def start_unixros_server(
    service_manager: ServiceManager,
    topic_manager: TopicManager,
    path: Path
) -> Tuple[Server, str]:
    server: Server = await start_unix_server(
        partial(handle, service_manager, topic_manager),
        path=path)
    return server, str(path)
