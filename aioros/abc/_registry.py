from abc import ABCMeta, abstractmethod
from typing import Dict, List, Tuple, Type

from ._msg import MessageT


class Registry(metaclass=ABCMeta):
    @property
    @abstractmethod
    def published_topics(self) -> Dict[str, Type[MessageT]]:
        ...

    @property
    @abstractmethod
    def subscribed_topics(self) -> Dict[str, Type[MessageT]]:
        ...

    @abstractmethod
    def publisher_update(self, topic_name: str, publishers: List[str]) -> None:
        ...

    @property
    @abstractmethod
    def connection_infos(self) -> List[Tuple[int, str, str, str, str, bool, str]]:
        ...
