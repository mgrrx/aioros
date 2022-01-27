__all__ = (
    "ServerHandle",
    "ServerProxy",
    "XmlRpcTypes",
    "handle",
    "start_server",
)

from ._client import ServerProxy
from ._protocol._common import XmlRpcTypes
from ._server import ServerHandle, handle, start_server

for key, value in list(locals().items()):
    if getattr(value, "__module__", "").startswith("aioros.xmlrpc."):
        value.__module__ = __name__
