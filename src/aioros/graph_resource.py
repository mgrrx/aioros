import os
import re
import sys

from .names import canonicalize_name
from .names import is_global
from .names import is_private
from .names import make_global_ns
from .names import ns_join
from .remappings import Remappings


NS_PATTERN = re.compile(r'^__ns:=(?P<ns>.*)')
MASTER_PATTERN = re.compile(r'^__master:=(?P<master>.+)')
ADDRESS_PATTERN = re.compile(r'^__(ip|hostname):=(?P<address>.+)')


def _get_ros_namespace() -> str:
    for arg in sys.argv:
        match = NS_PATTERN.match(arg)
        if match:
            return match.groupdict()['ns']

    return make_global_ns(os.environ.get('ROS_NAMESPACE', '/'))


def get_master_uri() -> str:
    for arg in sys.argv:
        match = MASTER_PATTERN.match(arg)
        if match:
            return match.groupdict()['master']

    return os.environ.get('ROS_MASTER_URI', 'http://localhost:11311')


def get_local_address() -> str:
    for arg in sys.argv:
        match = ADDRESS_PATTERN.match(arg)
        if match:
            return match.groupdict()['address']
    if 'ROS_HOSTNAME' in os.environ:
        return os.environ['ROS_HOSTNAME']
    if 'ROS_IP' in os.environ:
        return os.environ['ROS_IP']
    if os.environ.get('ROS_IPV6') == 'on':
        return '::'
    return '0.0.0.0'


class GraphResource:

    def __init__(self, node_name: str) -> None:
        self._namespace: str = _get_ros_namespace()
        self._node_name: str = ns_join(self._namespace, node_name)
        self._remappings = Remappings()

    @property
    def node_name(self) -> str:
        return self._node_name

    @property
    def namespace(self) -> str:
        return self._namespace

    def resolve(self, name: str) -> str:
        if not name:
            return self._namespace
        name = canonicalize_name(name)
        if is_global(name):
            resolved_name = name
        elif is_private(name):
            resolved_name = ns_join(self._node_name, name[1:])
        else:
            resolved_name = self._namespace + name

        return self._remappings.get(resolved_name, resolved_name)
