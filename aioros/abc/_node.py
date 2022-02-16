from abc import ABCMeta, abstractmethod
from types import TracebackType
from typing import Callable, Dict, Generic, List, Optional, Type

from genpy.rostime import Time

from ..xmlrpc._protocol._common import XmlRpcTypes
from ._action import Action, ActionClient, FeedbackT, GoalT, ResultT
from ._msg import MessageT, Service, ServiceRequestT, ServiceResponseT

Header = Dict[str, str]


class ServiceServer(Generic[ServiceRequestT, ServiceResponseT], metaclass=ABCMeta):
    @property
    @abstractmethod
    def service_type(self) -> Type[Service[ServiceRequestT, ServiceResponseT]]:
        ...

    @property
    @abstractmethod
    def service_name(self) -> str:
        ...

    @property
    def request_class(self) -> Type[ServiceRequestT]:
        return getattr(self.service_type, "_request_class")

    @property
    def response_class(self) -> Type[ServiceResponseT]:
        return getattr(self.service_type, "_response_class")

    @property
    @abstractmethod
    def header(self) -> Header:
        ...

    @abstractmethod
    async def serve(self) -> None:
        ...


class ServiceClient(Generic[ServiceRequestT, ServiceResponseT], metaclass=ABCMeta):
    async def __aenter__(self) -> "ServiceClient[ServiceRequestT, ServiceResponseT]":
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        pass

    @property
    @abstractmethod
    def service_type(self) -> Type[Service[ServiceRequestT, ServiceResponseT]]:
        ...

    @property
    @abstractmethod
    def service_name(self) -> str:
        ...

    @property
    def request_class(self) -> Type[ServiceRequestT]:
        return getattr(self.service_type, "._request_class")

    @property
    def response_class(self) -> Type[ServiceResponseT]:
        return getattr(self.service_type, "_response_class")

    @abstractmethod
    async def call(self, request: ServiceRequestT) -> ServiceResponseT:
        ...


class Subscription(Generic[MessageT], metaclass=ABCMeta):
    async def __aenter__(self) -> "Subscription[MessageT]":
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        pass

    def clone(self) -> "Subscription[MessageT]":
        ...

    @property
    @abstractmethod
    def topic_name(self) -> str:
        ...

    @property
    @abstractmethod
    def topic_type(self) -> Type[MessageT]:
        ...

    @abstractmethod
    async def wait_for_peers(self) -> None:
        ...

    def __aiter__(self) -> "Subscription[MessageT]":
        return self

    @abstractmethod
    async def __anext__(self) -> MessageT:
        ...


class Publication(Generic[MessageT], metaclass=ABCMeta):
    async def __aenter__(self) -> "Publication[MessageT]":
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        pass

    def clone(self) -> "Publication[MessageT]":
        ...

    @property
    @abstractmethod
    def topic_name(self) -> str:
        ...

    @property
    @abstractmethod
    def topic_type(self) -> Type[MessageT]:
        ...

    @property
    @abstractmethod
    def header(self) -> Header:
        ...

    @abstractmethod
    async def wait_for_peers(self) -> None:
        ...

    @abstractmethod
    async def publish(self, message: MessageT) -> None:
        ...


class Node(metaclass=ABCMeta):
    async def __aenter__(self) -> "Node":
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        await self.aclose()

    @abstractmethod
    async def aclose(self) -> None:
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def namespace(self) -> str:
        ...

    @property
    def full_name(self) -> str:
        return self.namespace + self.name

    @abstractmethod
    def is_running(self) -> bool:
        ...

    @property
    @abstractmethod
    def xmlrpc_uri(self) -> str:
        ...

    @property
    @abstractmethod
    def tcpros_uri(self) -> str:
        ...

    @property
    @abstractmethod
    def udsros_uri(self) -> str:
        ...

    @property
    @abstractmethod
    def master_uri(self) -> str:
        ...

    @abstractmethod
    def signal_shutdown(self, sleep_for: float = 0.0) -> None:
        ...

    @abstractmethod
    async def get_param(self, key: str) -> XmlRpcTypes:
        ...

    @abstractmethod
    async def get_param_default(self, key: str, default: XmlRpcTypes) -> XmlRpcTypes:
        ...

    @abstractmethod
    async def get_param_cached(self, key: str) -> XmlRpcTypes:
        ...

    @abstractmethod
    async def set_param(self, key: str, value: XmlRpcTypes) -> None:
        ...

    @abstractmethod
    async def delete_param(self, key: str) -> None:
        ...

    @abstractmethod
    async def has_param(self, key: str) -> bool:
        ...

    @abstractmethod
    async def search_param(self, key: str) -> XmlRpcTypes:
        ...

    @abstractmethod
    async def get_param_names(self) -> List[str]:
        ...

    @abstractmethod
    def create_server(
        self,
        service_name: str,
        service_type: Type[Service[ServiceRequestT, ServiceResponseT]],
        handler: Callable[[ServiceRequestT], ServiceResponseT],
    ) -> ServiceServer[ServiceRequestT, ServiceResponseT]:
        ...

    @abstractmethod
    def create_client(
        self,
        service_name: str,
        service_type: Type[Service[ServiceRequestT, ServiceResponseT]],
        *,
        persistent: bool = False
    ) -> ServiceClient[ServiceRequestT, ServiceResponseT]:
        ...

    @abstractmethod
    def create_subscription(
        self, topic_name: str, topic_type: Type[MessageT]
    ) -> Subscription[MessageT]:
        ...

    @abstractmethod
    def create_publication(
        self, topic_name: str, topic_type: Type[MessageT], *, latched: bool = False
    ) -> Publication[MessageT]:
        ...

    @abstractmethod
    def create_action_client(
        self,
        namespace: str,
        action: Type[Action[GoalT, FeedbackT, ResultT]],
    ) -> ActionClient[GoalT, FeedbackT, ResultT]:
        ...

    @abstractmethod
    def get_time(self) -> Time:
        ...
