from asyncio import get_event_loop
from os import getpid
from os import kill
from signal import SIGINT
from typing import Any
from typing import List
from typing import Tuple

from aiohttp.web import AppRunner
from aiohttp.web import Application
from aiohttp.web import TCPSite
from aiohttp_xmlrpc.handler import XMLRPCView

from ..tcpros.utils import split_tcpros_uri
from ..topic_manager import TopicManager
from ..param_manager import ParamManager


TopicInfo = Tuple[str, str]
StrResult = Tuple[int, str, str]
IntResult = Tuple[int, str, int]


class NodeAPI(XMLRPCView):

    def rpc_getName(
        self,
        caller_id: str
    ) -> StrResult:
        return 1, '', self.request.app['node_name']

    def rpc_getUri(
        self,
        caller_id: str
    ) -> StrResult:
        return 1, '', self.request.app['xmlrpc_uri']

    def rpc_getBusStats(
        self,
        caller_id: str
    ):
        # return 1, '', [pub_stats, sub_stats, []]
        return 1, '', [[], [], []]

    def rpc_getBusInfo(
        self,
        caller_id: str
    ) -> StrResult:
        return 1, 'bus info', '?'

    def rpc_getMasterUri(
        self,
        caller_id: str
    ) -> StrResult:
        master_uri = self.request.app['master_uri']
        return 1, master_uri, master_uri

    def rpc_shutdown(
        self,
        caller_id: str,
        msg: str=''
    ) -> IntResult:
        get_event_loop().call_soon(kill, getpid(), SIGINT)
        return 1, 'shutdown', 0

    def rpc_getPid(
        self,
        caller_id: str
    ) -> IntResult:
        return 1, '', getpid()

    def rpc_getSubscriptions(
        self,
        caller_id: str
    ) -> Tuple[int, str, List[TopicInfo]]:
        return 1, 'subscriptions', [
            (topic.name, topic.type_name)
            for topic in
            self.request.app['topic_manager'].topics.values()
            if topic.has_subscriptions
        ]

    def rpc_getPublications(
        self,
        caller_id: str
    ) -> Tuple[int, str, List[TopicInfo]]:
        return 1, 'publications', [
            (topic.name, topic.type_name)
            for topic in
            self.request.app['topic_manager'].topics.values()
            if topic.has_publishers
        ]

    def rpc_paramUpdate(
        self,
        caller_id: str,
        parameter_key: str,
        parameter_value: Any
    ) -> IntResult:
        success = self.request.app['param_manager'].update(
            parameter_key,
            parameter_value)
        return 1 if success else -1, '', 0

    def rpc_publisherUpdate(
        self,
        caller_id: str,
        topic: str,
        publishers: List[str]
    ) -> IntResult:
        topic = self.request.app['topic_manager'].topics.get(topic)
        if not topic:
            return 0, 'not connected to topic', 0
        topic.connect_to_publishers(publishers)
        return 1, '', 0

    def rpc_requestTopic(
        self,
        caller_id: str,
        topic: str,
        protocols: List[List[Any]]
    ) -> Tuple[int, str, List[Any]]:
        topic = self.request.app['topic_manager'].topics.get(topic)
        if not topic:
            return 0, 'topic not published', []
        for protocol in protocols:
            if protocol[0] == 'TCPROS':
                host, port = split_tcpros_uri(self.request.app['tcpros_uri'])
                return 1, '', ['TCPROS', host, port]
            elif protocol[0] == 'UNIXROS':
                return 1, '', ['UNIXROS', self.request.app['unixros_uri']]
        return 0, 'no supported protocol implementations', []


async def start_node_api_server(
    topic_manager: TopicManager,
    param_manager: ParamManager,
    node_name: str,
    master_uri: str,
    tcpros_uri: str,
    unixros_uri: str,
    host: str,
    port: int
) -> Tuple[AppRunner, str]:
    app = Application()
    app.router.add_route('*', '/', NodeAPI)
    runner = AppRunner(app)
    await runner.setup()
    site = TCPSite(runner, host, port)
    await site.start()

    port = site._server.sockets[0].getsockname()[1]
    xmlrpc_uri = f'http://{host}:{port}/'
    app['node_name'] = node_name
    app['master_uri'] = master_uri
    app['xmlrpc_uri'] = xmlrpc_uri
    app['tcpros_uri'] = tcpros_uri
    app['unixros_uri'] = unixros_uri
    app['topic_manager'] = topic_manager
    app['param_manager'] = param_manager

    return runner, xmlrpc_uri
