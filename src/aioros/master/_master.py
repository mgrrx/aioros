from dataclasses import dataclass, field

from anyio.abc import TaskGroup

from ._param_cache import ParamCache
from ._registry import Registry


@dataclass(eq=False)
class Master:
    xmlrpc_uri: str
    task_group: TaskGroup
    param_cache: ParamCache = field(init=False, default_factory=ParamCache)
    registry: Registry = field(init=False)

    def __post_init__(self) -> None:
        self.registry = Registry(self.task_group)
