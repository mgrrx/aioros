import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, NamedTuple, Set

import httpx
from anyio.abc import TaskGroup

from .._node._api import NodeApiClient

logger = logging.getLogger(__name__)


class Registration(NamedTuple):
    caller_id: str
    api: str


@dataclass(eq=False)
class Node:
    api: str
    services: Set[str] = field(init=False, default_factory=set)
    publications: Set[str] = field(init=False, default_factory=set)
    subscriptions: Set[str] = field(init=False, default_factory=set)
    client: NodeApiClient = field(init=False)

    def __post_init__(self) -> None:
        self.client = NodeApiClient(self.api, "master")

    @property
    def has_any_registration(self) -> bool:
        return any((self.services, self.publications, self.subscriptions))

    async def aclose(self) -> None:
        try:
            await self.client.aclose()
        except httpx.ConnectTimeout:
            pass

    async def publisher_update(self, topic: str, publishers: List[str]) -> None:
        try:
            await self.client.publisher_update(topic, publishers)
        except httpx.ConnectTimeout:
            logger.warning("Could not send publisher to %s", self.api)


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
    topic_types: Dict[str, str] = field(init=False, default_factory=dict)
    nodes: Dict[str, Node] = field(init=False, default_factory=dict)

    async def aclose(self) -> None:
        for node in self.nodes.values():
            await node.aclose()

    def _register_node(self, caller_id: str, caller_api: str) -> Node:
        if node := self.nodes.get(caller_id):
            if node.api == caller_api:
                return node

            self.task_group.start_soon(
                node.client.shutdown, "new node registered with same name"
            )
            self._unregister_all(caller_id)
            node = None

        node = Node(caller_api)
        self.nodes[caller_id] = node
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
            self.task_group.start_soon(node.aclose)

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
                # TODO this might be too greedy. We probably want a queue per node
                # and process this queue strictly sequential to ensure that only
                # the last update is sent
                # also unsent entries could be dropped before sending if there is a new
                # update to be sent
                self.task_group.start_soon(node.publisher_update, topic, publishers)

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
