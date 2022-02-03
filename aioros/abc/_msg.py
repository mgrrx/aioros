from io import BytesIO
from typing import Optional, Protocol, Type, TypeVar

from genpy import Message

ServiceRequestT = TypeVar("ServiceRequestT", bound=Message)
ServiceResponseT = TypeVar("ServiceResponseT", bound=Message)
MessageT = TypeVar("MessageT", bound=Message)


class Service(Protocol[ServiceRequestT, ServiceResponseT]):
    _type: str
    _md5sum: str
    _request_class: Type[ServiceRequestT]
    _response_class: Type[ServiceResponseT]


class AnyMsg(Message):
    """
    Message class to use for subscribing to any topic regardless
    of type. Incoming messages are not deserialized. Instead, the raw
    serialized data can be accssed via the buff property.
    """

    _md5sum: str = "*"
    _type: str = "*"
    _has_header: bool = False
    _full_text: str = ""
    __slots__ = ["_buff"]

    def __init__(self) -> None:
        super().__init__()
        self._buff: Optional[bytes] = None

    def serialize(self, buff: BytesIO) -> None:
        if self._buff is None:
            raise RuntimeError
        buff.write(self._buff)

    def deserialize(self, str_: bytes) -> None:
        self._buff = str_
