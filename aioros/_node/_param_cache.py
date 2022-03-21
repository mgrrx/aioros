from dataclasses import dataclass, field
from typing import Dict, Iterator

from .._utils._resolve import join, split
from ..xmlrpc import XmlRpcTypes


def iter_namespaces(key: str) -> Iterator[str]:
    splitted = list(split(key))
    for i in range(len(splitted)):
        yield join(*splitted[:i])
    yield key


@dataclass(eq=False)
class ParamCache:
    _params: Dict[str, XmlRpcTypes] = field(default_factory=dict, init=False)

    def __contains__(self, key: str) -> bool:
        key = join(*split(key))
        for namespace in iter_namespaces(key):
            if namespace in self._params:
                return True
        return False

    def __getitem__(self, key: str) -> XmlRpcTypes:
        key = join(*split(key))
        for namespace in iter_namespaces(key):
            if namespace in self._params:
                value = self._params[namespace]
                key = key[len(namespace) :]
                break
        else:
            raise KeyError(key)

        for namespace in split(key):
            if not isinstance(value, dict):
                raise KeyError(key)
            value = value[namespace]
        return value

    def add(self, key: str, value: XmlRpcTypes) -> None:
        key = join(*split(key))
        self._params[key] = value

    def delete(self, key: str) -> None:
        key = join(*split(key))
        for namespace in iter_namespaces(key):
            if namespace in self._params:
                self._delete_cache(namespace, key[len(namespace) :])

    def update(self, key: str, value: XmlRpcTypes) -> None:
        key = join(*split(key))
        for namespace in iter_namespaces(key):
            if namespace in self._params:
                self._update_cache(namespace, key[len(namespace) :], value)

    def _update_cache(self, namespace: str, key: str, value: XmlRpcTypes) -> None:
        splitted = list(split(key))
        if splitted:
            cache = self._params[namespace]
            for i, part in enumerate(splitted):
                if not isinstance(cache, dict):
                    raise KeyError(join(namespace, key))
                if i + 1 == len(splitted):
                    cache[part] = value
                elif part not in cache:
                    cache[part] = {}
                    cache = cache[part]
                else:
                    cache = cache[part]
        else:
            self._params[namespace] = value

    def _delete_cache(self, namespace: str, key: str) -> None:
        splitted = list(split(key))
        if not splitted:
            return

        cache = self._params[namespace]
        for i, part in enumerate(splitted):
            if not isinstance(cache, dict):
                raise KeyError(join(namespace, key))
            if i + 1 == len(splitted):
                del cache[part]
            elif part not in cache:
                return
            else:
                cache = cache[part]
