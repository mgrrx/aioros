from typing import Tuple


def split_tcpros_uri(tcpros_uri: str) -> Tuple[str, int]:
    host, port = tcpros_uri \
        .replace('rosrpc://', '') \
        .replace('/', '') \
        .split(':')[0:2]
    return host, int(port)
