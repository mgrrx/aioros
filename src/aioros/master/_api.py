import logging
import os
from functools import wraps
from typing import Any, Awaitable, Callable, List, Tuple, TypeVar, cast

import anyio
from anyio.abc import CancelScope

from ..xmlrpc import ServerHandle
from ._master import Master

AnyResult = Tuple[int, str, Any]
BoolResult = Tuple[int, str, bool]
IntResult = Tuple[int, str, int]
StrResult = Tuple[int, str, str]
TopicInfo = Tuple[str, str]

logger = logging.getLogger(__name__)

ReturnType = TypeVar("ReturnType")


async def _shutdown(scope: CancelScope, msg: str) -> None:
    logger.info("Shutting down in 1 second")
    await anyio.sleep(1)
    print("Shutting down:", msg)
    await scope.cancel()


def log(
    func: Callable[..., Awaitable[Tuple[int, str, ReturnType]]]
) -> Callable[..., Awaitable[Tuple[int, str, ReturnType]]]:
    @wraps(func)
    async def wrapper(
        this: ServerHandle, *args: Any, **kwargs: Any
    ) -> Tuple[int, str, ReturnType]:
        try:
            code, msg, value = await func(this, *args, **kwargs)
        except:
            logger.error("%s %s had an exception", func.__name__, args, exc_info=True)
            raise
        logger.debug("%s %s -> %s", func.__name__, args, (code, msg, value))
        return cast(Tuple[int, str, ReturnType], (code, msg, value))

    return wrapper


class MasterApiHandle(ServerHandle):
    # pylint: disable=invalid-name,no-self-use

    def __init__(self, master: Master) -> None:
        super().__init__()
        self._master = master

    @log
    async def getPid(self, caller_id: str) -> IntResult:
        # pylint: disable=unused-argument
        return 1, "", os.getpid()

    @log
    async def getUri(self, caller_id: str) -> StrResult:
        # pylint: disable=unused-argument
        return 1, "", self._master.xmlrpc_uri

    @log
    async def shutdown(self, caller_id: str, msg: str = "") -> IntResult:
        # pylint: disable=unused-argument
        await self._master.task_group.spawn(
            _shutdown, self._master.task_group.cancel_scope, msg
        )
        return 1, "shutdown", 0

    @log
    async def getParam(self, caller_id: str, key: str) -> AnyResult:
        # pylint: disable=unused-argument
        try:
            return 1, "", self._master.param_cache[key]
        except KeyError:
            return -1, f"Parameter [{key}] is not set", 0

    @log
    async def setParam(self, caller_id: str, key: str, value: Any) -> IntResult:
        # pylint: disable=unused-argument
        self._master.param_cache[key] = value
        # TODO self._reg_man.on_param_update(key, value, caller_id)
        return 1, "", 0

    @log
    async def deleteParam(self, caller_id: str, key: str) -> IntResult:
        # pylint: disable=unused-argument
        try:
            del self._master.param_cache[key]
        except KeyError:
            return -1, f"Parameter [{key}] is not set", 0
        # TODO self._reg_man.on_param_update(key, {}, caller_id)
        return 1, "", 0

    @log
    async def searchParam(self, caller_id: str, key: str) -> AnyResult:
        try:
            return 1, "", self._master.param_cache.search(key, caller_id)
        except KeyError:
            return -1, "", 0

    @log
    async def hasParam(self, caller_id: str, key: str) -> BoolResult:
        # pylint: disable=unused-argument
        return 1, "", key in self._master.param_cache

    @log
    async def getParamNames(self, caller_id: str) -> Tuple[int, str, List[str]]:
        # pylint: disable=unused-argument
        return 1, "", list(self._master.param_cache.keys())

    @log
    async def lookupNode(self, caller_id: str, node_name: str) -> StrResult:
        # pylint: disable=unused-argument
        try:
            return 1, "", self._master.registry.nodes[node_name].api
        except KeyError:
            return -1, "", f"unknown node {node_name}"

    @log
    async def lookupService(self, caller_id: str, service: str) -> StrResult:
        # pylint: disable=unused-argument
        try:
            return 1, "", self._master.registry.services[service].api
        except KeyError:
            return -1, "", f"unknown service {service}"

    @log
    async def registerService(
        self,
        caller_id: str,
        service: str,
        service_api: str,  # tcpros_uri
        caller_api: str,
    ) -> IntResult:
        self._master.registry.register_service(
            service, caller_id, caller_api, service_api
        )
        return 1, "", 1

    @log
    async def unregisterService(
        self, caller_id: str, service: str, service_api: str
    ) -> IntResult:
        # pylint: disable=unused-argument
        self._master.registry.unregister_service(service, caller_id)
        return 1, "", 1

    @log
    async def registerSubscriber(
        self, caller_id: str, topic: str, topic_type: str, caller_api: str
    ) -> Tuple[int, str, List[str]]:
        self._master.registry.register_subscriber(
            topic, topic_type, caller_id, caller_api
        )
        return (
            1,
            "",
            [reg.api for reg in self._master.registry.publications.get(topic, [])],
        )

    @log
    async def unregisterSubscriber(
        self, caller_id: str, topic: str, caller_api: str
    ) -> IntResult:
        self._master.registry.unregister_subscriber(topic, caller_id, caller_api)
        return 1, "", 1

    @log
    async def registerPublisher(
        self, caller_id: str, topic: str, topic_type: str, caller_api: str
    ) -> Tuple[int, str, List[str]]:
        self._master.registry.register_publisher(
            topic, topic_type, caller_id, caller_api
        )
        return (
            1,
            "",
            [reg.api for reg in self._master.registry.subscriptions.get(topic, [])],
        )

    @log
    async def unregisterPublisher(
        self, caller_id: str, topic: str, caller_api: str
    ) -> IntResult:
        self._master.registry.unregister_publisher(topic, caller_id, caller_api)
        return 1, "", 1

    @log
    async def getPublishedTopics(
        self, caller_id: str, subgraph: str
    ) -> Tuple[int, str, List[Tuple[str, str]]]:
        # pylint: disable=unused-argument
        return (
            1,
            "",
            [
                (topic, self._master.registry.topic_types[topic])
                for topic in self._master.registry.publications
                if topic.startswith(subgraph)
            ],
        )

    @log
    async def getTopicTypes(
        self, caller_id: str
    ) -> Tuple[int, str, List[Tuple[str, str]]]:
        # pylint: disable=unused-argument
        return (
            1,
            "",
            [
                (topic, self._master.registry.topic_types[topic])
                for topic in self._master.registry.publications
            ],
        )

    @log
    async def getSystemState(
        self, caller_id: str
    ) -> Tuple[
        int,
        str,
        Tuple[
            List[Tuple[str, List[str]]],
            List[Tuple[str, List[str]]],
            List[Tuple[str, List[str]]],
        ],
    ]:
        # pylint: disable=unused-argument
        return (
            1,
            "",
            (
                [
                    (topic, [publisher.caller_id for publisher in publishers])
                    for topic, publishers in self._master.registry.publications.items()
                    if publishers
                ],
                [
                    (topic, [subscriber.caller_id for subscriber in subscribers])
                    for topic, subscribers in self._master.registry.subscriptions.items()
                    if subscribers
                ],
                [
                    (service_name, [service.caller_id])
                    for service_name, service in self._master.registry.services.items()
                ],
            ),
        )
