import logging
import sys
from contextvars import ContextVar

import anyio
from rosgraph_msgs.msg import Log
from std_msgs.msg import Header

from .. import abc
from .._utils import _logging as base_logging
from ._context import UninitializedNodeError, full_node_name, node

logdebug = logging.getLogger("rosout").debug
loginfo = logging.getLogger("rosout").info
logwarn = logging.getLogger("rosout").warning
logerr = logging.getLogger("rosout").error
logfatal = logging.getLogger("rosout").critical

level_map = {
    logging.DEBUG: Log.DEBUG,
    logging.INFO: Log.INFO,
    logging.WARNING: Log.WARN,
    logging.ERROR: Log.ERROR,
    logging.CRITICAL: Log.FATAL,
}


class ColoredFormatter(base_logging.ColoredFormatter):
    def format(self, record: logging.LogRecord) -> str:
        try:
            setattr(record, "node_name", full_node_name())
        except UninitializedNodeError:
            setattr(record, "node_name", "UNSET")
        return super().format(record)


def init_logging(log_level: int = logging.INFO) -> None:
    formatter = ColoredFormatter(
        "%(asctime)s %(node_name)s[%(process)d] %(message)s",
        "%b %d %H:%M:%S",
    )

    base_logging.init_logging(
        formatter,
        log_level=log_level,
    )
    rosout = logging.getLogger("rosout")
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    rosout.addHandler(console_handler)
    rosout.addHandler(RosOutHandler())
    rosout.setLevel(log_level)
    rosout.propagate = False


class RosOutHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            node_ = node.get()
            rosout_logger.get().publish(
                Log(
                    level=level_map[record.levelno],
                    name=node_.full_name,
                    msg=self.format(record),
                    file=record.filename,
                    line=record.lineno,
                    function=record.funcName,
                    header=Header(stamp=node_.get_time()),
                )
            )
        except LookupError:
            pass


class RosoutLogger:
    def __init__(self) -> None:
        (
            self._send_stream,
            self._receive_stream,
        ) = anyio.create_memory_object_stream(float("inf"), Log)

    def publish(self, log: Log) -> None:
        self._send_stream.send_nowait(log)

    async def serve(self, ros_node: abc.Node) -> None:
        async with ros_node.create_publication("/rosout", Log) as publisher:
            async with self._receive_stream:
                async for log in self._receive_stream:
                    await publisher.publish(log)


rosout_logger: ContextVar[RosoutLogger] = ContextVar("rosout_logger")
