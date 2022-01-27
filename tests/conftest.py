import logging

import pytest

from aioros._utils._logging import ColoredFormatter, init_logging

init_logging(
    ColoredFormatter(
        "%(asctime)s.%(msecs)d [%(name)s] %(message)s",
        "%b %d %H:%M:%S",
    ),
    log_level=logging.DEBUG,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"
