from abc import ABCMeta, abstractmethod
from io import BytesIO
from typing import List, Optional, Protocol, Type, TypeVar, runtime_checkable

from std_msgs.msg import Header


class Message(Protocol):
    _md5sum: str
    _type: str
    _has_header: bool
    _full_text: str
    _slot_types = List[str]

    @abstractmethod
    def _get_types(self) -> List[str]:
        ...

    @abstractmethod
    def _check_types(self, exc: Optional[Exception] = None) -> None:
        pass

    @abstractmethod
    def serialize(self, buff: BytesIO) -> None:
        ...

    @abstractmethod
    def deserialize(self, str_: bytes) -> None:
        ...


@runtime_checkable
class MessageWithHeader(Message, Protocol, metaclass=ABCMeta):
    header: Header


MessageT = TypeVar("MessageT", bound=Message)
MessageWithHeaderT = TypeVar("MessageWithHeaderT", bound=MessageWithHeader)
ServiceRequestT = TypeVar("ServiceRequestT", bound=Message)
ServiceResponseT = TypeVar("ServiceResponseT", bound=Message)


class Service(Protocol[ServiceRequestT, ServiceResponseT]):
    _type: str
    _md5sum: str
    _request_class: Type[ServiceRequestT]
    _response_class: Type[ServiceResponseT]
