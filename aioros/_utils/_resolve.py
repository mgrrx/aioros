import os
import re
import sys
from typing import Dict, Iterator, Optional

from ..abc import Remapping

VALID_NAME = re.compile(r"^(?a:[a-zA-Z]\w*)$")


def resolve_name(name: str, node_name: str, namespace: str) -> str:
    resolved = _resolve_name(name, node_name, namespace)
    for part in resolved.split("/"):
        if part and VALID_NAME.match(part) is None:
            raise ValueError(
                f"Name '{part}' of '{resolved}' is not a valid ROS resource name"
            )
    return resolved


def _resolve_name(name: str, node_name: str, namespace: str) -> str:
    if not name:
        return namespace

    canonical_name = join(name)
    if name.startswith("/"):
        return f"/{canonical_name}"
    if canonical_name.startswith("~"):
        return "/" + join(namespace, node_name, canonical_name[1:])
    return "/" + join(namespace, canonical_name)


def split(key: str) -> Iterator[str]:
    return (i for i in key.split("/") if i)


def join(*args: str) -> str:
    return "/".join(i for arg in args for i in arg.split("/") if i)


def _matches(pattern_str: str) -> Iterator[re.Match]:
    pattern = re.compile(pattern_str)
    for arg in sys.argv:
        if match := pattern.match(arg):
            yield match


def get_mappings() -> Remapping:
    mappings = {}
    for match in _matches(r"^(?P<src>(\~)?[a-zA-Z0-9][\w\/]+):=(?P<dst>.+)$"):
        dct: Dict[str, str] = match.groupdict()
        mappings[dct["src"]] = dct["dst"]
    return mappings


def get_remapped_name() -> Optional[str]:
    for match in _matches(r"^__name:=(?P<name>.+)$"):
        return match.groupdict()["name"]
    return None


def get_master_uri() -> str:
    for match in _matches(r"^__master:=(?P<master>.+)$"):
        return match.groupdict()["master"]
    return os.environ.get("ROS_MASTER_URI", "http://localhost:11311")


def get_namespace() -> str:
    for match in _matches(r"^__ns:=(?P<ns>(.+))$"):
        return match.groupdict()["ns"]
    return os.environ.get("ROS_NAMESPACE", "/")


def validate_namespace(namespace: str) -> bool:
    return re.match(r"^(/[a-zA-Z]\w*)*/$", namespace) is not None


def get_local_address() -> str:
    for match in _matches(r"^__(ip|hostname):=(?P<address>.+)$"):
        return match.groupdict()["address"]
    if hostname := os.getenv("ROS_HOSTNAME"):
        return hostname
    if address := os.getenv("ROS_IP"):
        return address
    return "::" if os.environ.get("ROS_IPV6") == "on" else "0.0.0.0"


def normalize_namespace(namespace: str) -> str:
    if namespace.startswith("~"):
        raise ValueError("Cannot resolve private names") from None

    if not namespace.startswith("/"):
        namespace = "/" + namespace

    if not namespace.endswith("/"):
        namespace += "/"

    return namespace
