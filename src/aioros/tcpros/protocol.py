from asyncio import StreamReader
from contextlib import contextmanager
from io import BytesIO
from itertools import count
from struct import Struct
from typing import BinaryIO
from typing import Counter
from typing import Dict
from typing import Generator

from genpy import Message

_struct_B: Struct = Struct('<B')
_struct_I: Struct = Struct('<I')


class Serializer:

    def __init__(self):
        self._buf: BinaryIO = BytesIO()
        self._seq: Counter = count(1)

    @contextmanager
    def serialize(self, msg: Message) -> Generator[bytes, None, None]:
        if getattr(msg.__class__, "_has_header", False):
            header = msg.header
            header.seq = next(self._seq)
            if header.frame_id is None:
                header.frame_id = "0"

        self._buf.seek(4)

        msg.serialize(self._buf)

        size = self._buf.tell() - 4
        self._buf.seek(0)
        self._buf.write(_struct_I.pack(size))
        try:
            yield self._buf.getvalue()
        finally:
            self._buf.truncate(0)
            self._buf.seek(0)


async def read_header(reader: StreamReader) -> Dict[str, str]:
    size_bytes = await reader.readexactly(4)
    size: int = _struct_I.unpack(size_bytes)[0]
    header = await reader.readexactly(size)
    return decode_header(header)


def decode_header(data: bytes) -> Dict[str, str]:
    header_dict = {}
    start = 0
    while start < len(data):
        field_size = _struct_I.unpack(data[start:start+4])[0]
        start += field_size + 4
        line = data[start-field_size:start].decode()
        idx = line.find("=")
        header_dict[line[:idx].strip()] = line[idx+1:]
    return header_dict


def encode_header(header: Dict[str, str]) -> bytes:
    data = b''
    for key, value in sorted(header.items()):
        key_value = key.encode() + b'=' + value.encode()
        data += _struct_I.pack(len(key_value)) + key_value
    return _struct_I.pack(len(data)) + data


async def read_byte(reader: StreamReader) -> int:
    return _struct_B.unpack(await reader.readexactly(1))[0]


def encode_byte(value: int) -> bytes:
    return _struct_B.pack(value)


def encode_str(value: str) -> bytes:
    value_in_bytes = value.encode()
    size = len(value_in_bytes)
    return Struct(f'<{size}s').pack(value_in_bytes)


async def read_error(reader: StreamReader) -> str:
    size_bytes = await reader.readexactly(4)
    size: int = _struct_I.unpack(size_bytes)[0]
    data = await read_data(reader)
    return Struct(f'<{size}s').unpack(data)[0]


async def read_data(reader: StreamReader) -> bytes:
    size_bytes = await reader.readexactly(4)
    size: int = _struct_I.unpack(size_bytes)[0]
    return await reader.readexactly(size)
