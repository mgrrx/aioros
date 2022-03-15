import logging
import signal
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path
from typing import AsyncIterator, Awaitable, Callable, Dict, List, Optional, Tuple, Type

import anyio
from anyio.abc import SocketStream, TaskGroup, TaskStatus
from anyio.streams.buffered import BufferedByteReceiveStream
from genpy.rostime import Time
from rosgraph_msgs.msg import Clock

from .. import abc
from .._utils._resolve import (
    get_local_address,
    get_mappings,
    get_master_uri,
    get_namespace,
    get_remapped_name,
    normalize_namespace,
    resolve_name,
)
from .._utils._sockets import create_tcp_listener, create_unix_listener
from ..abc._registry import Registry as AbstractRegistry
from ..xmlrpc import XmlRpcTypes
from ..xmlrpc import handle as handle_xmlrpc
from ._action._client import ActionClient
from ._api import MasterApiClient, NodeApiHandle
from ._context import node
from ._logging import RosoutLogger, init_logging, rosout_logger
from ._param_cache import ParamCache
from ._tcpros._protocol import encode_header, read_header
from ._tcpros._service_client import NonPersistentServiceClient, PersistentServiceClient
from ._tcpros._service_server import ServiceServer
from ._tcpros._topic_publisher import LatchedPublication, Publication
from ._tcpros._topic_subscriber import Subscription, SubscriptionManager
from ._tcpros._utils import ProtocolError

logger = logging.getLogger(__name__)


async def delayed(sleep_for: float, callback: Callable) -> None:
    await anyio.sleep(sleep_for)
    callback()


@dataclass
class Registry(AbstractRegistry):
    services: Dict[str, ServiceServer] = field(default_factory=dict, init=False)
    publications: Dict[str, Publication] = field(default_factory=dict, init=False)
    subscriptions: Dict[str, SubscriptionManager] = field(
        default_factory=dict, init=False
    )

    def get_publication_handler(
        self, key: str
    ) -> Callable[[str, abc.Header, SocketStream], Awaitable[None]]:
        return self.publications[key].handle_tcpros

    def get_service_handler(
        self, key: str
    ) -> Callable[[str, abc.Header, SocketStream], Awaitable[None]]:
        return self.services[key].handle_tcpros

    @property
    def published_topics(self) -> Dict[str, Type[abc.MessageT]]:
        return {
            topic_name: publication.topic_type
            for topic_name, publication in self.publications.items()
        }

    @property
    def subscribed_topics(self) -> Dict[str, Type[abc.MessageT]]:
        return {
            topic_name: manager.topic_type
            for topic_name, manager in self.subscriptions.items()
        }

    @property
    def connection_infos(self) -> List[Tuple[int, str, str, str, str, bool, str]]:
        return [
            (
                publisher.id,
                publisher.xmlrpc_uri,
                "i",
                publisher.protocol,
                manager.topic_name,
                publisher.connected,
                "",  # TODO
            )
            for manager in self.subscriptions.values()
            for publisher in manager.connected_publishers.values()
        ] + [
            (
                1,
                subscriber.node_name,
                "o",
                subscriber.protocol,
                publication.topic_name,
                True,
                "",
            )
            for publication in self.publications.values()
            for subscriber in publication._subscribers
        ]

    def publisher_update(self, topic_name: str, publishers: List[str]) -> None:
        if topic_name in self.subscriptions:
            self.subscriptions[topic_name].update_publishers(publishers)


class Node(abc.Node):
    def __init__(
        self,
        *,
        task_group: TaskGroup,
        name: str,
        namespace: str,
        master_uri: str,
        xmlrpc_uri: str,
        tcpros_uri: str,
        udsros_uri: str,
        registry: Registry,
        param_cache: ParamCache,
        remapping: abc.Remapping,
    ) -> None:
        self._task_group = task_group
        self._name = name
        self._namespace = namespace
        self._xmlrpc_uri = xmlrpc_uri
        self._tcpros_uri = tcpros_uri
        self._udsros_uri = udsros_uri
        self._registry = registry
        self._param_cache = param_cache
        self._master = MasterApiClient(master_uri, self)
        self._remapping = remapping
        self._time: Optional[Time] = None

    async def __aenter__(self) -> abc.Node:
        await self._master.__aenter__()
        return self

    async def aclose(self) -> None:
        await self._master.aclose()

    def signal_shutdown(self, sleep_for: float = 0.0) -> None:
        self._task_group.start_soon(
            delayed, sleep_for, self._task_group.cancel_scope.cancel
        )

    def is_running(self) -> bool:
        return not self._task_group.cancel_scope.cancel_called

    @property
    def name(self) -> str:
        return self._name

    @property
    def namespace(self) -> str:
        return self._namespace

    @property
    def xmlrpc_uri(self) -> str:
        return self._xmlrpc_uri

    @property
    def tcpros_uri(self) -> str:
        return self._tcpros_uri

    @property
    def udsros_uri(self) -> str:
        return self._udsros_uri

    @property
    def master_uri(self) -> str:
        return self._master.uri

    def _resolve_name(self, key: str) -> str:
        resolved_name = resolve_name(key, self.name, self.namespace)
        return self._remapping.get(resolved_name, resolved_name)

    async def get_param(self, key: str) -> XmlRpcTypes:
        key = self._resolve_name(key)
        if key in self._param_cache:
            return self._param_cache[key]

        value = await self._master.get_param(key)
        self._param_cache.update(key, value)
        return value

    async def get_param_cached(self, key: str) -> XmlRpcTypes:
        key = self._resolve_name(key)
        if key in self._param_cache:
            return self._param_cache[key]
        # Not yet registered
        value = await self._master.subscribe_param(key)
        self._param_cache.add(key, value)
        if isinstance(value, dict) and not value:
            raise KeyError(key)
        return value

    async def get_param_default(self, key: str, default: XmlRpcTypes) -> XmlRpcTypes:
        try:
            return await self.get_param(key)
        except KeyError:
            return default

    async def set_param(self, key: str, value: XmlRpcTypes) -> None:
        key = self._resolve_name(key)
        await self._master.set_param(key, value)
        self._param_cache.update(key, value)

    async def delete_param(self, key: str) -> None:
        key = self._resolve_name(key)
        await self._master.delete_param(key)
        self._param_cache.delete(key)

    async def has_param(self, key: str) -> bool:
        key = self._resolve_name(key)
        return await self._master.has_param(key)

    async def search_param(self, key: str) -> XmlRpcTypes:
        key = self._resolve_name(key)
        return await self._master.search_param(key)

    async def get_param_names(self) -> List[str]:
        return await self._master.get_param_names()

    def create_server(
        self,
        service_name: str,
        service_type: Type[abc.Service[abc.ServiceRequestT, abc.ServiceResponseT]],
        handler: Callable[[abc.ServiceRequestT], Awaitable[abc.ServiceResponseT]],
    ) -> abc.ServiceServer[abc.ServiceRequestT, abc.ServiceResponseT]:
        service_name = self._resolve_name(service_name)
        if service_name in self._registry.services:
            raise ValueError(f"Service {service_name} is already registered!")
        server = ServiceServer(
            service_name, service_type, handler, self._master, self.full_name
        )
        self._registry.services[service_name] = server
        return server

    def create_client(
        self,
        service_name: str,
        service_type: Type[abc.Service[abc.ServiceRequestT, abc.ServiceResponseT]],
        *,
        persistent: bool = False,
    ) -> abc.ServiceClient[abc.ServiceRequestT, abc.ServiceResponseT]:
        service_name = self._resolve_name(service_name)
        cls = PersistentServiceClient if persistent else NonPersistentServiceClient
        return cls(service_name, service_type, self._master, self.full_name)

    def create_subscription(
        self, topic_name: str, topic_type: Type[abc.MessageT]
    ) -> abc.Subscription[abc.MessageT]:
        topic_name = self._resolve_name(topic_name)
        if topic_name not in self._registry.subscriptions:
            self._registry.subscriptions[topic_name] = SubscriptionManager(
                self._task_group,
                topic_name,
                topic_type,
                self._master,
                self.full_name,
            )
        return Subscription(self._registry.subscriptions[topic_name])

    def create_publication(
        self, topic_name: str, topic_type: Type[abc.MessageT], *, latched: bool = False
    ) -> abc.Publication[abc.MessageT]:
        topic_name = self._resolve_name(topic_name)
        cls = LatchedPublication if latched else Publication
        if topic_name not in self._registry.publications:
            self._registry.publications[topic_name] = cls(
                topic_name, topic_type, self._master, self.full_name
            )
        publication = self._registry.publications[topic_name]
        if type(publication) is not cls:  # pylint: disable=unidiomatic-typecheck
            raise ValueError(
                f"Publication was already created with latched={not latched}"
            )
        return publication

    def create_action_client(
        self,
        namespace: str,
        action: Type[abc.Action[abc.GoalT, abc.FeedbackT, abc.ResultT]],
    ) -> abc.ActionClient[abc.GoalT, abc.FeedbackT, abc.ResultT]:
        namespace = self._resolve_name(namespace)
        return ActionClient(self, self._task_group, namespace, action)

    def get_time(self) -> Time:
        return self._time or Time.from_sec(time.time())

    async def handle_tcpros(self, protocol: str, client: SocketStream) -> None:
        async with client:
            buffered_receiver = BufferedByteReceiveStream(client)
            try:
                header = await read_header(buffered_receiver)
                try:
                    if "service" in header:
                        handler_getter = self._registry.get_service_handler
                        key = "service"
                    elif "topic" in header:
                        handler_getter = self._registry.get_publication_handler
                        key = "topic"
                    else:
                        await client.send(
                            encode_header(
                                dict(error="no topic or service name detected")
                            )
                        )
                        return

                    try:
                        handler = handler_getter(header[key])
                    except KeyError as exc:
                        raise ProtocolError(
                            f"{key} {header[key]} is not provided by this node"
                        ) from exc
                    else:
                        await handler(protocol, header, client)
                except ProtocolError as err:
                    await client.send(encode_header(dict(error=err.args[0])))
            except anyio.IncompleteRead:
                # Raised if the connection is closed before the requested amount of
                # bytes has been read.
                pass

    async def manage_time(
        self, *, task_status: TaskStatus = anyio.TASK_STATUS_IGNORED
    ) -> None:
        use_sim_time = await self.get_param_default("/use_sim_time", False)
        if not use_sim_time:
            task_status.started()
        else:
            self._time = Time(0, 0)
            task_status.started()
            async with self.create_subscription("/clock", Clock) as subscription:
                async for clock in subscription:
                    self._time = clock.clock


async def _signal_handler(
    ros_node: Node, *, task_status: TaskStatus = anyio.TASK_STATUS_IGNORED
) -> None:
    async with anyio.open_signal_receiver(signal.SIGINT, signal.SIGTERM) as signals:
        task_status.started()
        async for signum in signals:
            if signum == signal.SIGINT:
                print("Ctrl+C pressed!")
            else:
                print("Terminated!")

            ros_node.signal_shutdown()
            return


@asynccontextmanager
async def init_node(
    node_name: str,
    *,
    xmlrpc_port: int = 0,
    tcpros_port: int = 0,
    udsros_path: Optional[Path] = None,
    namespace: Optional[str] = None,
    master_uri: Optional[str] = None,
    local_address: Optional[str] = None,
    remapping: Optional[abc.Remapping] = None,
    register_signal_handler: bool = True,
    initialize_time: bool = True,
    configure_logging: bool = True,
    debug: bool = False,
) -> AsyncIterator[abc.Node]:
    # TODO validate node name
    local_address = local_address or get_local_address()
    remapping = remapping or get_mappings()
    master_uri = master_uri or get_master_uri()
    namespace = normalize_namespace(namespace or get_namespace())
    node_name = get_remapped_name() or node_name
    if configure_logging:
        init_logging(logging.DEBUG if debug else logging.INFO)

    async with anyio.create_task_group() as task_group:

        xmlrpc_listener, xmlrpc_uri = await create_tcp_listener(
            local_address, xmlrpc_port, "http://{local_host}:{local_port}/"
        )

        tcpros_listener, tcpros_uri = await create_tcp_listener(
            local_address, tcpros_port, "rosrpc://{local_host}:{local_port}"
        )

        udsros_listener, udsros_uri = await create_unix_listener(
            local_address,
            namespace + node_name,
            udsros_path,
            "udsros://{local_host}/{path}",
        )
        logger.info("Initializing ROS node [%s]", xmlrpc_uri)

        registry = Registry()
        param_cache = ParamCache()
        ros_node = Node(
            task_group=task_group,
            name=node_name,
            namespace=namespace,
            master_uri=master_uri,
            xmlrpc_uri=xmlrpc_uri,
            tcpros_uri=tcpros_uri,
            udsros_uri=udsros_uri,
            registry=registry,
            param_cache=param_cache,
            remapping=remapping,
        )

        if register_signal_handler:
            await task_group.start(_signal_handler, ros_node)

        async with ros_node:
            token = node.set(ros_node)

            task_group.start_soon(
                xmlrpc_listener.serve,
                partial(handle_xmlrpc, NodeApiHandle(ros_node, registry, param_cache)),
            )
            task_group.start_soon(
                tcpros_listener.serve, partial(ros_node.handle_tcpros, "TCPROS")
            )
            task_group.start_soon(
                udsros_listener.serve, partial(ros_node.handle_tcpros, "UDSROS")
            )
            async with anyio.create_task_group() as sub_task_group:

                if initialize_time:
                    await sub_task_group.start(ros_node.manage_time)

                if configure_logging:
                    _rosout_logger = RosoutLogger()
                    sub_task_group.start_soon(_rosout_logger.serve, ros_node)
                    logger_token = rosout_logger.set(_rosout_logger)

                yield ros_node

                sub_task_group.cancel_scope.cancel()

            # Main terminated, clean up
            task_group.cancel_scope.cancel()

            # clean up context
            node.reset(token)

            if configure_logging:
                rosout_logger.reset(logger_token)
