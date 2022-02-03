from typing import Tuple

from ... import abc


class ProtocolError(ValueError):
    pass


def split_tcpros_uri(tcpros_uri: str) -> Tuple[str, int]:
    host, port = tcpros_uri.replace("rosrpc://", "").replace("/", "").split(":")[0:2]
    return host, int(port)


def split_udsros_uri(unxiros_uri: str) -> Tuple[str, str]:
    bits = unxiros_uri.replace("udsros://", "").split("/")
    return bits[0], "/".join(bits[1:])


def require_fields(header: abc.Header, *fields: str) -> None:
    for field in fields:
        if field not in header:
            raise ProtocolError(f"Missing required '{field}' field")


def check_md5sum(header: abc.Header, md5sum: str) -> None:
    if header["md5sum"] not in ("*", md5sum):
        raise ProtocolError(
            f"request from [{header['callerid']}]: "
            f"md5sums do not match: [{header['md5sum']}] vs. [{md5sum}]"
        )
