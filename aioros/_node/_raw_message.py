from io import BytesIO
from typing import Optional

from genpy import Message


class RawMessage(Message):
    """
    Message class to use for subscribing to any topic regardless
    of type. Incoming messages are not deserialized. Instead, the raw
    serialized data can be accessed via the raw property.
    """

    _md5sum: str = "*"
    _type: str = "*"
    _has_header: bool = False
    _full_text: str = ""
    __slots__ = ["raw"]

    def __init__(self) -> None:
        super().__init__()
        self.raw: Optional[bytes] = None

    def serialize(self, buff: BytesIO) -> None:
        if self.raw is None:
            raise RuntimeError
        buff.write(self.raw)

    def deserialize(self, str_: bytes) -> None:
        self.raw = str_
