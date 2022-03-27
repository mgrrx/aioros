from genpy import Time
from geometry_msgs.msg import TransformStamped

from ..abc import MessageWithHeaderT

class TransformException(Exception):
    pass

class ConnectivityException(TransformException):
    pass

class LookupException(TransformException):
    pass

class ExtrapolationException(TransformException):
    pass

class InvalidArgumentException(TransformException):
    pass

class TimeoutException(TransformException):
    pass

class BufferCore:
    def __init__(self, cache_time: float = 10.0) -> None: ...
    def set_transform(
        self, transform: TransformStamped, authority: str, is_static: bool = False
    ) -> None: ...
    def transform(
        self,
        object_stamped: MessageWithHeaderT,
        target_frame: str,
    ) -> MessageWithHeaderT: ...
    def transform_full(
        self,
        object_stamped: MessageWithHeaderT,
        target_frame: str,
        target_time: Time,
        fixed_frame: str,
    ) -> MessageWithHeaderT: ...
    def lookup_transform(
        self,
        target_frame: str,
        source_frame: str,
        time: Time,
    ) -> TransformStamped: ...
    def lookup_transform_full(
        self,
        target_frame: str,
        target_time: Time,
        source_frame: str,
        source_time: Time,
        fixed_frame: str,
    ) -> TransformStamped: ...
    def can_transform(
        self,
        target_frame: str,
        source_frame: str,
        time: Time,
    ) -> bool: ...
    def can_transform_full(
        self,
        target_frame: str,
        target_time: Time,
        source_frame: str,
        source_time: Time,
        fixed_frame: str,
    ) -> bool: ...
    def clear(self) -> None: ...
    def all_frames_as_string(self) -> str: ...
    def all_frames_as_yaml(self, current_time: float = 0.0) -> str: ...
