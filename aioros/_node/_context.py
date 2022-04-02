from contextvars import ContextVar
from functools import wraps
from typing import Any, AsyncIterator, Awaitable, Callable, List, Type, TypeVar

from genpy import Duration, Time

from .. import abc
from ..xmlrpc import XmlRpcTypes

node: ContextVar[abc.Node] = ContextVar("node")


class UninitializedNodeError(Exception):
    pass


ReturnType = TypeVar("ReturnType")


def require_node(func: Callable[..., ReturnType]) -> Callable[..., ReturnType]:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> ReturnType:
        try:
            node.get()
        except LookupError as err:
            raise UninitializedNodeError() from err
        else:
            return func(*args, **kwargs)

    return wrapper


@require_node
def node_name() -> str:
    return node.get().name


@require_node
def full_node_name() -> str:
    return node.get().full_name


@require_node
def resolve_name(key: str) -> str:
    return node.get().resolve_name(key)


@require_node
def is_running() -> bool:
    return node.get().is_running()


@require_node
async def get_param(key: str) -> XmlRpcTypes:
    return await node.get().get_param(key)


@require_node
async def get_param_default(key: str, default: XmlRpcTypes) -> XmlRpcTypes:
    return await node.get().get_param_default(key, default)


@require_node
async def get_param_cached(key: str) -> XmlRpcTypes:
    return await node.get().get_param_cached(key)


@require_node
async def set_param(key: str, value: XmlRpcTypes) -> None:
    return await node.get().set_param(key, value)


@require_node
async def delete_param(key: str) -> None:
    return await node.get().delete_param(key)


@require_node
async def has_param(key: str) -> bool:
    return await node.get().has_param(key)


@require_node
async def search_param(key: str) -> XmlRpcTypes:
    return await node.get().search_param(key)


@require_node
async def get_param_names() -> List[str]:
    return await node.get().get_param_names()


@require_node
def create_server(
    service_name: str,
    service_type: Type[abc.Service[abc.ServiceRequestT, abc.ServiceResponseT]],
    handler: Callable[[abc.ServiceRequestT], Awaitable[abc.ServiceResponseT]],
) -> abc.ServiceServer[abc.ServiceRequestT, abc.ServiceResponseT]:
    return node.get().create_server(service_name, service_type, handler)


@require_node
def create_client(
    service_name: str,
    service_type: Type[abc.Service[abc.ServiceRequestT, abc.ServiceResponseT]],
    *,
    persistent: bool = False
) -> abc.ServiceClient[abc.ServiceRequestT, abc.ServiceResponseT]:
    return node.get().create_client(service_name, service_type, persistent=persistent)


@require_node
def create_subscription(
    topic_name: str, topic_type: Type[abc.MessageT]
) -> abc.Subscription[abc.MessageT]:
    return node.get().create_subscription(topic_name, topic_type)


@require_node
def create_publication(
    topic_name: str, topic_type: Type[abc.MessageT], *, latched: bool = False
) -> abc.Publication[abc.MessageT]:
    return node.get().create_publication(topic_name, topic_type, latched=latched)


@require_node
def create_action_client(
    namespace: str,
    action: Type[abc.Action[abc.GoalT, abc.FeedbackT, abc.ResultT]],
) -> abc.ActionClient[abc.GoalT, abc.FeedbackT, abc.ResultT]:
    return node.get().create_action_client(namespace, action)


@require_node
def get_time() -> Time:
    return node.get().get_time()


@require_node
async def sleep(duration: Duration) -> None:
    await node.get().sleep(duration)


@require_node
async def every(duration: Duration) -> AsyncIterator[Time]:
    async for time in node.get().every(duration):
        yield time
