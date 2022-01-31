from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator

from .._utils._resolve import split


@dataclass(eq=False)
class ParamCache:
    _params: Dict[str, Any] = field(default_factory=dict, init=False)

    def __contains__(self, key: str) -> bool:
        try:
            self[key]
        except KeyError:
            return False
        return True

    def __getitem__(self, key: str) -> Any:
        value = self._params
        for namespace in split(key):
            if not isinstance(value, dict):
                raise KeyError(key)
            value = value[namespace]
        return value

    def __setitem__(self, key: str, value: Any) -> None:
        if key == "/":
            if not isinstance(value, dict):
                raise ValueError()
            self._params = value
            return
        splitted = list(split(key))
        params = self._params
        for namespace in splitted[:-1]:
            if namespace not in params or not isinstance(params[namespace], dict):
                params[namespace] = {}
            params = params[namespace]
        params[splitted[-1]] = value

    def __delitem__(self, key: str) -> None:
        splitted = list(split(key))
        namespace = "/" + "/".join(splitted[:-1])
        subkey = splitted[-1]
        del self[namespace][subkey]

    def keys(self) -> Iterator[str]:
        worklist = deque(sorted(self._params.items()))
        while worklist:
            key, value = worklist.popleft()
            if isinstance(value, dict):
                worklist.extendleft((f"{key}/{k}", v) for k, v in sorted(value.items()))
            else:
                yield "/" + key

    def search(self, key: str, namespace: str) -> Any:
        if key.startswith("/"):
            if key in self:
                return key
            return None

        key_ns = next(split(key))

        if f"{namespace}/{key_ns}" in self:
            return f"{namespace}/{key}"

        splitted = list(split(namespace))
        for i in range(1, len(splitted) + 1):
            search_key = "/" + "/".join(splitted[:-i] + [key_ns])
            if search_key in self:
                return "/" + "/".join(splitted[:-i] + [key])

        return None
