from asyncio import get_event_loop
from asyncio import iscoroutinefunction
from collections import defaultdict
from typing import Any
from typing import Callable
from typing import Dict
from typing import NamedTuple
from typing import Set
from typing import Tuple

from .api.master_api_client import MasterApiClient


CallbackFunc = Callable[[str, Any], None]


class Callback(NamedTuple):
    callback: CallbackFunc


class ParamManager:

    def __init__(self, master_api_client: MasterApiClient) -> None:
        self._master_api_client: MasterApiClient = master_api_client
        self._callbacks: Dict[str, Set[Callback]] = defaultdict(set)
        self._cache = {}

    async def subscribe_param(
        self,
        key: str,
        callback: CallbackFunc
    ) -> Tuple[Any, Callback]:
        if key not in self._callbacks:
            param_value = await self._master_api_client.subscribe_param(key)
            self._cache[key] = param_value
        else:
            param_value = self._cache[key]
        cb = Callback(callback)
        self._callbacks[key].add(cb)
        return param_value, cb

    async def unsubscribe_callback(
        self,
        callback: Callback
    ) -> bool:
        for key, callbacks in self._callbacks.items():
            if callback in callbacks:
                callbacks.discard(callback)
                break
        else:
            return False
        if not callbacks:
            await self._master_api_client.unsusbcribe_param(key)
            self._cache.pop(key)
            self._callbacks.pop(key)
        return True

    def update(self, key: str, value: Any) -> bool:
        self._cache[key] = value

        callbacks = set()
        namespace = '/'
        for ns in key.split('/'):
            if not ns:
                continue
            namespace += ns
            callbacks |= set(self._callbacks.get(namespace, set()))
            namespace += '/'

        if callbacks is None:
            return False
        loop = get_event_loop()
        for callback in callbacks:
            if iscoroutinefunction(callback.callback):
                loop.create_task(callback.callback(key, value))
            else:
                loop.call_soon(callback.callback, key, value)
        return True
