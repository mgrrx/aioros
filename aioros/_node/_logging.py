import logging

from .._utils import _logging as base_logging
from ._context import UninitializedNodeError, full_node_name


class ColoredFormatter(base_logging.ColoredFormatter):
    def format(self, record: logging.LogRecord) -> str:
        try:
            setattr(record, "node_name", full_node_name())
        except UninitializedNodeError:
            setattr(record, "node_name", "UNSET")
        return super().format(record)


def init_logging(log_level: int = logging.INFO) -> None:
    base_logging.init_logging(
        ColoredFormatter(
            "%(asctime)s %(node_name)s[%(process)d] %(message)s",
            "%b %d %H:%M:%S",
        ),
        log_level=log_level,
    )
