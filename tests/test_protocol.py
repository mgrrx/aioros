from typing import Dict

import pytest
from std_msgs.msg import String

from aioros._node._tcpros._protocol import (
    Serializer,
    decode_header,
    encode_header,
    serialize,
)


@pytest.mark.parametrize(
    ("header"),
    [
        {},
        {"foo": "bar"},
        {"a": "b", "c": "1"},
        {"x": "="},
        {"=": "="},
    ],
)
def test_encode_decode(header: Dict[str, str]) -> None:
    assert decode_header(encode_header(header)[4:]) == header


@pytest.mark.parametrize(
    ("header"),
    [
        {"": ""},
        {"": "1"},
    ],
)
def test_encode_empty_decode(header: Dict[str, str]) -> None:
    assert decode_header(encode_header(header)[4:]) == {}


def test_serializer() -> None:
    msg = String()
    msg.data = "test"
    serializer = Serializer()
    data = serializer.serialize(msg)
    msg2 = String()
    msg2.deserialize(data[4:])
    assert msg.data == msg2.data


def test_serialize() -> None:
    msg = String()
    msg.data = "test"
    data = serialize(msg)
    msg2 = String()
    msg2.deserialize(data[4:])
    assert msg.data == msg2.data
