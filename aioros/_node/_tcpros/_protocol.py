from io import BytesIO
from itertools import count
from struct import Struct, pack, unpack
from typing import Generic

from anyio.streams.buffered import BufferedByteReceiveStream

from ... import abc

_struct_B: Struct = Struct("<B")
_struct_I: Struct = Struct("<I")


def serialize(message: abc.MessageT, buf: BytesIO = None) -> bytes:
    buf = buf or BytesIO()
    buf.seek(4)

    message.serialize(buf)

    size = buf.tell() - 4
    buf.seek(0)
    buf.write(_struct_I.pack(size))
    return buf.getvalue()


class Serializer(Generic[abc.MessageT]):
    def __init__(self) -> None:
        self._buf = BytesIO()
        self._seq = count(1)

    def serialize(self, msg: abc.MessageT) -> bytes:
        if getattr(msg.__class__, "_has_header", False):
            if msg.header.seq is None:
                msg.header.seq = next(self._seq)
            if msg.header.frame_id is None:
                msg.header.frame_id = "0"

        data = serialize(msg, self._buf)
        self._buf.truncate(0)
        self._buf.seek(0)
        return data


async def read_header(buffered_stream: BufferedByteReceiveStream) -> abc.Header:
    size_bytes = await buffered_stream.receive_exactly(4)
    size: int = _struct_I.unpack(size_bytes)[0]
    header = await buffered_stream.receive_exactly(size)
    return decode_header(header)


def decode_header(data: bytes) -> abc.Header:
    header_dict = {}
    start = 0
    while start < len(data):
        field_size = _struct_I.unpack(data[start : start + 4])[0]
        start += field_size + 4
        line = data[start - field_size : start].decode()
        idx = line.find("=", 1)
        if idx == -1:
            continue
        header_dict[line[:idx].strip()] = line[idx + 1 :]
    return header_dict


def encode_header(header: abc.Header) -> bytes:
    data = b""
    for key, value in sorted(header.items()):
        key_value = key.encode() + b"=" + value.encode()
        data += _struct_I.pack(len(key_value)) + key_value
    return _struct_I.pack(len(data)) + data


async def read_byte(buffered_stream: BufferedByteReceiveStream) -> int:
    return _struct_B.unpack(await buffered_stream.receive_exactly(1))[0]


def encode_byte(value: int) -> bytes:
    return _struct_B.pack(value)


def encode_str(value: str) -> bytes:
    value_in_bytes = value.encode()
    size = len(value_in_bytes)
    return pack(f"<{size}s", value_in_bytes)


async def read_error(buffered_stream: BufferedByteReceiveStream) -> str:
    size_bytes = await buffered_stream.receive_exactly(4)
    size: int = _struct_I.unpack(size_bytes)[0]
    data = await read_data(buffered_stream)
    return unpack(f"<{size}s", data)[0]


async def read_data(buffered_stream: BufferedByteReceiveStream) -> bytes:
    size_bytes = await buffered_stream.receive_exactly(4)
    size: int = _struct_I.unpack(size_bytes)[0]
    return await buffered_stream.receive_exactly(size)
