__all__ = ("init_master", "run", "Master")

from ._master import Master
from ._server import init_master, run

for key, value in list(locals().items()):
    if getattr(value, "__module__", "").startswith("aioros.master."):
        value.__module__ = __name__
