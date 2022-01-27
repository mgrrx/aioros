import logging
import sys

RED = "\x1b[31m"
GREEN = "\x1b[32m"
YELLOW = "\x1b[33m"
RESET = "\x1b[39m"


class ColoredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        if record.levelno <= logging.DEBUG:
            return GREEN + super().format(record) + RESET
        if record.levelno >= logging.ERROR:
            return RED + super().format(record) + RESET
        if record.levelno >= logging.WARNING:
            return YELLOW + super().format(record) + RESET
        return super().format(record)


def init_logging(formatter: logging.Formatter, log_level: int = logging.INFO) -> None:
    logger = logging.getLogger("aioros")
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    logger.setLevel(log_level)
    logger.propagate = False
