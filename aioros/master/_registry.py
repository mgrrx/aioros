import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Dict, Iterator, List, NamedTuple, Set

import httpx
from anyio import create_memory_object_stream
from anyio.abc import TaskGroup
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream

from .._node._api import NodeApiClient, XmlRpcTypes
from .._utils._resolve import join, normalize_namespace, split

logger = logging.getLogger(__name__)


def compute_all_keys(key: str, value: Dict[str, XmlRpcTypes]) -> Iterator[str]:
    for k, v in value.items():
        _key = key + k + "/"
        yield _key
        if isinstance(v, dict):
            yield from compute_all_keys(_key, v)


class Registration(NamedTuple):
    caller_id: str
    api: str


class Task(NamedTuple):
    method: Callable[..., Coroutine[Any, Any, Any]]
    args: List[Any]


@dataclass(eq=False)
class Node:
    api: str
    services: Set[str] = field(init=False, default_factory=set)
    publications: Set[str] = field(init=False, default_factory=set)
    subscriptions: Set[str] = field(init=False, default_factory=set)
    param_subscriptions: Set[str] = field(init=False, default_factory=set)
    send_stream: MemoryObjectSendStream[Task] = field(init=False)
    receive_stream: MemoryObjectReceiveStream[Task] = field(init=False)

    def __post_init__(self) -> None:
        self.send_stream, self.receive_stream = create_memory_object_stream(
            float("inf"), Task
        )

    async def serve(self) -> None:
        async with NodeApiClient(self.api, "master") as client:
            async for task in self.receive_stream:
                logger.debug(
                    "Calling node %s %s %s", self.api, task.method.__name__, task.args
                )
                try:
                    await task.method(client, *task.args)
                except httpx.ConnectTimeout:
                    pass

    @property
    def has_any_registration(self) -> bool:
        return any(
            (
                self.services,
                self.publications,
                self.subscriptions,
                self.param_subscriptions,
            )
        )

    def publisher_update(self, topic: str, publishers: List[str]) -> None:
        self.send_stream.send_nowait(
            Task(NodeApiClient.publisher_update, [topic, publishers])
        )

    def param_update(self, key: str, value: XmlRpcTypes) -> None:
        self.send_stream.send_nowait(Task(NodeApiClient.param_update, [key, value]))

    def shutdown(self, msg: str) -> None:
        self.send_stream.send_nowait(Task(NodeApiClient.shutdown, [msg]))


@dataclass(eq=False)
class Registry:
    task_group: TaskGroup
    services: Dict[str, Registration] = field(init=False, default_factory=dict)
    publications: Dict[str, Set[Registration]] = field(
        init=False, default_factory=lambda: defaultdict(set)
    )
    subscriptions: Dict[str, Set[Registration]] = field(
        init=False, default_factory=lambda: defaultdict(set)
    )
    param_subscribers: Dict[str, Set[Registration]] = field(
        init=False, default_factory=lambda: defaultdict(set)
    )
    topic_types: Dict[str, str] = field(init=False, default_factory=dict)
    nodes: Dict[str, Node] = field(init=False, default_factory=dict)

    def _register_node(self, caller_id: str, caller_api: str) -> Node:
        if node := self.nodes.get(caller_id):
            if node.api == caller_api:
                return node

            node.shutdown("new node registered with same name")
            self._unregister_all(caller_id)
            node = None

        node = Node(caller_api)
        self.nodes[caller_id] = node
        self.task_group.start_soon(node.serve)
        return node

    def _register_topic(self, topic: str, topic_type: str) -> None:
        if topic_type != "*" and topic not in self.topic_types:
            self.topic_types[topic] = topic_type

    def _check_topic(self, topic: str) -> None:
        if topic not in self.publications and topic not in self.subscriptions:
            self.topic_types.pop(topic, None)

    def _check_node(self, caller_id: str) -> None:
        node = self.nodes.get(caller_id)
        if node and not node.has_any_registration:
            del self.nodes[caller_id]
            node.send_stream.close()

    def _unregister_all(self, caller_id: str) -> None:
        for service in list(self.services.keys()):
            if self.services[service].caller_id == caller_id:
                del self.services[service]

        for topic, registrations in self.publications.items():
            for reg in list(registrations):
                if reg.caller_id == caller_id:
                    registrations.remove(reg)
                    self._update_subscribers(topic)

        for registrations in self.subscriptions.values():
            for reg in list(registrations):
                if reg.caller_id == caller_id:
                    registrations.remove(reg)

    def _update_subscribers(self, topic: str) -> None:
        publishers = [
            registration.api for registration in self.publications.get(topic, [])
        ]
        for registration in self.subscriptions.get(topic, set()):
            if node := self.nodes.get(registration.caller_id):
                node.publisher_update(topic, publishers)

    def register_service(
        self, name: str, caller_id: str, caller_api: str, service_api: str
    ) -> None:
        self._register_node(caller_id, caller_api).services.add(name)
        self.services[name] = Registration(caller_id, service_api)

    def unregister_service(self, service: str, caller_id: str) -> None:
        self.services.pop(service, None)
        if node := self.nodes.get(caller_id):
            node.services.discard(service)
            self._check_node(caller_id)

    def register_subscriber(
        self, topic: str, topic_type: str, caller_id: str, caller_api: str
    ) -> None:
        self._register_topic(topic, topic_type)
        self._register_node(caller_id, caller_api).subscriptions.add(topic)
        self.subscriptions[topic].add(Registration(caller_id, caller_api))

    def unregister_subscriber(
        self, topic: str, caller_id: str, caller_api: str
    ) -> None:
        if topic in self.subscriptions:
            self.subscriptions[topic].discard(Registration(caller_id, caller_api))
            if not self.subscriptions[topic]:
                del self.subscriptions[topic]

        if node := self.nodes.get(caller_id):
            node.subscriptions.discard(topic)
            self._check_node(caller_id)

        self._check_topic(topic)

    def register_publisher(
        self, topic: str, topic_type: str, caller_id: str, caller_api: str
    ) -> None:
        self._register_topic(topic, topic_type)
        self._register_node(caller_id, caller_api).publications.add(topic)
        self.publications[topic].add(Registration(caller_id, caller_api))
        self._update_subscribers(topic)

    def unregister_publisher(self, topic: str, caller_id: str, caller_api: str) -> None:
        if topic in self.publications:
            self.publications[topic].discard(Registration(caller_id, caller_api))
            if not self.publications[topic]:
                del self.publications[topic]

        if node := self.nodes.get(caller_id):
            node.publications.discard(topic)
            self._check_node(caller_id)

        self._check_topic(topic)
        self._update_subscribers(topic)

    def register_param_subscriber(
        self, key: str, caller_id: str, caller_api: str
    ) -> None:
        key = normalize_namespace(join(key))
        self._register_node(caller_id, caller_api).param_subscriptions.add(key)

        self.param_subscribers[key].add(Registration(caller_id, caller_api))

    def unregister_param_subscriber(
        self, key: str, caller_id: str, caller_api: str
    ) -> None:
        key = normalize_namespace(join(key))

        if key in self.param_subscribers:
            self.param_subscribers[key].discard(Registration(caller_id, caller_api))
            if not self.param_subscribers[key]:
                del self.param_subscribers[key]

        if node := self.nodes.get(caller_id):
            node.param_subscriptions.discard(key)
            self._check_node(caller_id)

    def on_param_update(
        self, param_key: str, param_value: XmlRpcTypes, caller_id_to_ignore: str
    ) -> None:
        if not self.param_subscribers:
            return

        param_key = normalize_namespace(join(param_key))

        if isinstance(param_value, dict):
            all_keys = set(compute_all_keys(param_key, param_value))
        else:
            all_keys = None

        logger.debug("subscribers %s", self.param_subscribers)

        for key, subscribers in self.param_subscribers.items():
            if param_key.startswith(key):
                value = param_value
                key = param_key
            elif (
                all_keys is not None
                and key.startswith(param_key)
                and key not in all_keys
            ):
                value = {}
            else:
                continue

            for registration in subscribers:
                if registration.caller_id == caller_id_to_ignore:
                    continue

                node = self.nodes[registration.caller_id]
                node.param_update(key[:-1], value)

        if all_keys is None:
            return

        for key in all_keys:
            if key not in self.param_subscribers:
                continue

            sub_key = key[len(param_key) :]
            value = param_value
            for ns in split(sub_key):
                value = value[ns]

            for registration in self.param_subscribers[key]:
                node = self.nodes[registration.caller_id]
                node.param_update(key[:-1], value)
