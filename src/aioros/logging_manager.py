import logging

from rosgraph_msgs.msg import Log

from .tcpros.publisher import Publisher


MAPPING = {
    logging.DEBUG: Log.DEBUG,
    logging.INFO: Log.INFO,
    logging.WARNING: Log.WARN,
    logging.ERROR: Log.ERROR,
    logging.CRITICAL: Log.FATAL,
}


class LoggingHandler(logging.Handler):

    def __init__(
        self,
        node_name: str,
        publisher: Publisher,
        level: int = logging.NOTSET,
    ) -> None:
        self._node_name = node_name
        self._publisher = publisher
        super().__init__(level)

    def emit(self, record: logging.LogRecord):
        self._publisher.publish(Log(
            level=MAPPING.get(record.levelno, logging.DEBUG),
            name=self._node_name,
            msg=record.msg,
            file=record.pathname,
            function=record.funcName or '',
            line=record.lineno))


class LoggingManager:

    def __init__(
        self,
        node_name: str,
        publisher: Publisher
    ) -> None:
        self._publisher = publisher
        self._handler = LoggingHandler(node_name, publisher)
        logging.getLogger('rosout').addHandler(self._handler)
        logging.getLogger('rosout').setLevel(logging.INFO)

    async def close(self):
        logging.getLogger('rosout').removeHandler(self._handler)
        await self._publisher.close()
        self._publisher = None
        self._handler = None


async def start_logging_manager(node_handle):
    return LoggingManager(
        node_handle.node_name,
        await node_handle.create_publisher('/rosout', Log))
