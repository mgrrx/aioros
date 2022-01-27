import logging
import os
from typing import Any, List, Tuple, TypeVar, cast

from anyio.abc import AsyncResource

from .. import abc
from ..abc._registry import Registry
from ..xmlrpc import ServerHandle, ServerProxy, XmlRpcTypes
from ._tcpros._utils import split_tcpros_uri, split_udsros_uri

logger = logging.getLogger(__name__)

TopicInfo = Tuple[str, str]
StrResult = Tuple[int, str, str]
IntResult = Tuple[int, str, int]
TApiClient = TypeVar("TApiClient", bound="BaseApiClient")
PublishStats = Tuple[str, int, List[Tuple[int, int, int, bool]]]
SubscribeStats = Tuple[str, List[Tuple[int, int, int, int, bool]]]
ServiceStats = Tuple[()]


class XMLRPCError(Exception):
    pass


def validate(code: int, key: str, msg: str) -> None:
    if code == -1:
        raise KeyError(key) from None
    if code != 1:
        raise XMLRPCError(msg) from None


class BaseApiClient(AsyncResource):
    def __init__(self, uri: str) -> None:
        self._proxy: ServerProxy = ServerProxy(uri)

    @property
    def uri(self) -> str:
        """Return URI of proxy."""
        return self._proxy.url

    async def __aenter__(self: TApiClient) -> TApiClient:
        await self._proxy.__aenter__()
        return self

    async def aclose(self) -> None:
        await self._proxy.aclose()


class MasterApiClient(BaseApiClient):
    """ROS Master API Client"""

    def __init__(self, uri: str, node: abc.Node) -> None:
        self._node = node
        super().__init__(uri)

    async def delete_param(self, key: str) -> None:
        """Delete parameter."""
        code, msg, _ = await self._proxy.deleteParam(self._node.full_name, key)
        validate(code, key, msg)

    async def set_param(self, key: str, value: XmlRpcTypes) -> None:
        """Set parameter."""
        code, msg, _ = await self._proxy.setParam(self._node.full_name, key, value)
        validate(code, key, msg)

    async def get_param(self, key: str) -> XmlRpcTypes:
        """Retrieve parameter value from server."""
        code, msg, value = await self._proxy.getParam(self._node.full_name, key)
        validate(code, key, msg)
        return value

    async def has_param(self, key: str) -> bool:
        """Check if parameter is stored on server."""
        code, msg, value = await self._proxy.hasParam(self._node.full_name, key)
        validate(code, key, msg)
        return cast(bool, value)

    async def search_param(self, key: str) -> XmlRpcTypes:
        """Search for parameter key on the Parameter Server.

        Search starts in caller's namespace and proceeds upwards through parent
        namespaces until Parameter Server finds a matching key.
        """
        code, msg, value = await self._proxy.searchParam(self._node.full_name, key)
        validate(code, key, msg)
        return value

    async def get_param_names(self) -> List[str]:
        """Get list of all parameter names stored on this server."""
        code, msg, value = await self._proxy.getParamNames(self._node.full_name)
        if code != 1:
            raise XMLRPCError(msg) from None
        return cast(List[str], value)

    async def subscribe_param(self, key: str) -> XmlRpcTypes:
        """Retrieve parameter value from server and subscribe to updates to that
        parameter.
        """
        code, msg, value = await self._proxy.subscribeParam(
            self._node.full_name, self._node.xmlrpc_uri, key
        )
        if code != 1:
            raise XMLRPCError(msg) from None
        return value

    async def unsubscribe_param(self, key: str) -> int:
        """Unsubscribe from server to no longer retrieve parameter updates on key.

        :returns: number of subscriptions this node has on the parameter. If it is 0 it
        means that there was no ubscription so far.
        """
        code, msg, value = await self._proxy.unsubscribeParam(
            self._node.full_name, self._node.xmlrpc_uri, key
        )
        if code != 1:
            raise XMLRPCError(msg) from None
        return cast(int, value)

    async def lookup_node(self, node_name: str) -> str:
        """Get the XML-RPC URI of the node with the associated name/caller_id.
        This API is for looking information about publishers and subscribers.
        Use lookup_service instead to lookup ROS-RPC URIs.
        """
        code, msg, value = await self._proxy.lookupNode(self._node.full_name, node_name)
        if code != 1:
            raise XMLRPCError(msg) from None
        return cast(str, value)

    async def lookup_service(self, service: str) -> str:
        """Lookup all provider of a particular service."""
        code, msg, value = await self._proxy.lookupService(
            self._node.full_name, service
        )
        if code != 1:
            raise XMLRPCError(msg) from None
        return cast(str, value)

    async def get_published_topics(self, subgraph: str = "") -> List[Tuple[str, str]]:
        """Get list of topics that can be subscribed to. This does not return topics
        that have no publishers.
        """
        code, msg, value = await self._proxy.getPublishedTopics(
            self._node.full_name, subgraph
        )
        if code != 1:
            raise XMLRPCError(msg) from None
        return cast(List[Tuple[str, str]], value)

    async def register_service(self, service: str) -> None:
        """Register the caller as a provider of the specified service."""
        logger.debug("register_service %s", service)
        code, msg, _ = await self._proxy.registerService(
            self._node.full_name,
            service,
            self._node.tcpros_uri,
            self._node.xmlrpc_uri,
        )
        if code != 1:
            raise XMLRPCError(msg) from None

    async def unregister_service(self, service: str) -> int:
        """Unregister the caller as a provider of the specified service."""
        logger.debug("unregister_service %s", service)
        code, msg, value = await self._proxy.unregisterService(
            self._node.full_name, service, self._node.tcpros_uri
        )
        if code != 1:
            raise XMLRPCError(msg) from None
        return cast(int, value)

    async def register_subscriber(self, topic: str, topic_type: str) -> List[str]:
        """Subscribe the caller to the specified topic.
        In addition to receiving a list of current publishers, the subscriber will also
        receive notifications of new publishers via the publisher_update API."""
        code, msg, value = await self._proxy.registerSubscriber(
            self._node.full_name, topic, topic_type, self._node.xmlrpc_uri
        )
        if code != 1:
            raise XMLRPCError(msg) from None
        logger.debug("register_subscriber %s %s %s", topic, topic_type, value)
        return cast(List[str], value)

    async def unregister_subscriber(self, topic: str) -> int:
        """Unregister the caller as a publisher of the topic."""
        logger.debug("unregister_subscriber %s", topic)
        code, msg, value = await self._proxy.unregisterSubscriber(
            self._node.full_name, topic, self._node.xmlrpc_uri
        )
        if code != 1:
            raise XMLRPCError(msg) from None
        return cast(int, value)

    async def register_publisher(self, topic: str, topic_type: str) -> List[str]:
        """Register the caller as a publisher the topic."""
        code, msg, value = await self._proxy.registerPublisher(
            self._node.full_name, topic, topic_type, self._node.xmlrpc_uri
        )
        if code != 1:
            raise XMLRPCError(msg) from None
        logger.debug("register_publisher %s %s %s", topic, topic_type, value)
        return cast(List[str], value)

    async def unregister_publisher(self, topic: str) -> int:
        """Unregister the caller as a publisher of the topic."""
        logger.debug("unregister_publisher %s", topic)
        code, msg, value = await self._proxy.unregisterPublisher(
            self._node.full_name, topic, self._node.xmlrpc_uri
        )
        if code != 1:
            raise XMLRPCError(msg) from None
        return cast(int, value)


class NodeApiClient(BaseApiClient):
    def __init__(self, uri: str, node_name: str) -> None:
        super().__init__(uri)
        self._node_name = node_name

    async def request_topic(
        self, resolved_topic: str, protocols: List[List[str]]
    ) -> List[XmlRpcTypes]:
        """Publisher node API method called by a subscriber node.

        This requests that source allocate a channel for communication. Subscriber
        provides a list of desired protocols for communication. Publisher returns the
        selected protocol along with any additional params required for establishing
        connection. For example, for a TCP/IP-based connection, the source node may
        return a port number of TCP/IP server.
        """
        code, msg, value = await self._proxy.requestTopic(
            self._node_name, resolved_topic, protocols
        )
        if code != 1:
            raise XMLRPCError(msg) from None

        return cast(List[XmlRpcTypes], value)

    async def shutdown(self, msg: str = "") -> None:
        """Stop this node."""
        code, msg, _ = await self._proxy.shutdown(self._node_name, msg)
        if code != 1:
            raise XMLRPCError(msg) from None

    async def param_update(self, key: str, value: XmlRpcTypes) -> None:
        code, msg, _ = await self._proxy.paramUpdate(self._node_name, key, value)
        if code != 1:
            raise XMLRPCError(msg) from None

    async def publisher_update(self, topic: str, publishers: List[str]) -> None:
        logger.debug(
            "Updating %s about new publishers on %s %s", self.uri, topic, publishers
        )
        code, msg, _ = await self._proxy.publisherUpdate(
            self._node_name, topic, publishers
        )
        if code != 1:
            raise XMLRPCError(msg) from None


class NodeApiHandle(ServerHandle):
    # pylint: disable=invalid-name
    def __init__(self, node: abc.Node, registry: Registry):
        self._node = node
        self._registry = registry

    async def getName(self, caller_id: str) -> StrResult:
        """Retrieve name of this node."""
        # pylint: disable=unused-argument
        return 1, "", self._node.full_name

    async def getUri(self, caller_id: str) -> StrResult:
        """Retrieve XML RPC URI of this node."""
        # pylint: disable=unused-argument
        return 1, "", self._node.xmlrpc_uri

    async def getBusStats(
        self, caller_id: str
    ) -> Tuple[
        int, str, Tuple[List[PublishStats], List[SubscribeStats], List[ServiceStats]]
    ]:
        """Retrieve transport/topic statistics."""
        # pylint: disable=unused-argument, no-self-use
        # TODO implement me
        return 1, "", ([], [], [])

    async def getBusInfo(
        self, caller_id: str
    ) -> Tuple[int, str, List[Tuple[int, str, str, str, str, bool, str]]]:
        """Retrieve transport/topic connection information."""
        # pylint: disable=unused-argument, no-self-use
        return 1, "bus info", self._registry.connection_infos

    async def getMasterUri(self, caller_id: str) -> StrResult:
        """Get the URI of the master node."""
        # pylint: disable=unused-argument
        return 1, self._node.master_uri, self._node.master_uri

    async def shutdown(self, caller_id: str, msg: str = "") -> IntResult:
        """Stop this server."""
        # pylint: disable=unused-argument
        self._node.signal_shutdown(sleep_for=1.0)
        return 1, "shutdown", 0

    async def getPid(self, caller_id: str) -> IntResult:
        """Get the PID of this server."""
        # pylint: disable=unused-argument, no-self-use
        return 1, "", os.getpid()

    async def getSubscriptions(
        self, caller_id: str
    ) -> Tuple[int, str, List[TopicInfo]]:
        """Retrieve a list of topics that this node subscribes to."""
        # pylint: disable=unused-argument
        return (
            1,
            "subscriptions",
            [
                (topic_name, getattr(topic_type, "_type"))
                for topic_name, topic_type in self._registry.subscribed_topics.items()
            ],
        )

    async def getPublications(self, caller_id: str) -> Tuple[int, str, List[TopicInfo]]:
        """Retrieve a list of topics that this node publishes."""
        # pylint: disable=unused-argument
        return (
            1,
            "publications",
            [
                (topic_name, getattr(topic_type, "_type"))
                for topic_name, topic_type in self._registry.published_topics.items()
            ],
        )

    async def paramUpdate(
        self, caller_id: str, parameter_key: str, parameter_value: Any
    ) -> IntResult:
        """Callback from master with updated value of subscribed parameter."""
        # pylint: disable=unused-argument
        # TODO
        return -1, "", 0

    async def publisherUpdate(
        self, caller_id: str, topic: str, publishers: List[str]
    ) -> IntResult:
        """Callback from master of current publisher list for specified topic."""
        logger.debug("publisherUpdate %s %s %s", caller_id, topic, publishers)
        self._registry.publisher_update(topic, publishers)
        return 1, "", 0

    async def requestTopic(
        self, caller_id: str, topic: str, protocols: List[List[Any]]
    ) -> Tuple[int, str, List[Any]]:
        """Publisher node API method called by a subscriber node.

        This requests that source allocate a channel for communication. Subscriber
        provides a list of desired protocols for communication. Publisher returns the
        selected protocol along with any additional params required for establishing
        connection. For example, for a TCP/IP-based connection, the source node may
        return a port number of TCP/IP server.
        """
        # pylint: disable=unused-argument
        if topic not in self._registry.published_topics:
            return 0, "topic not published", []
        for protocol, *_ in protocols:
            if protocol == "TCPROS":
                host, port = split_tcpros_uri(self._node.tcpros_uri)
                return 1, "", [protocol, host, port]
            if protocol == "UDSROS":
                host, path = split_udsros_uri(self._node.udsros_uri)
                return 1, "", [protocol, host, path]
        return 0, "no supported protocol implementations", []
