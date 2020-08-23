from typing import Dict


class Service:

    def __init__(self, manager,  node_name, srv_name, srv_type, callback):
        self._manager = manager
        self._srv_name = srv_name
        self._srv_type = srv_type
        self.callback = callback
        self._header: Dict[str, str] = dict(
            callerid=node_name,
            md5sum=self.md5sum,
            service=self.name,
            type=self.type_name
        )

    @property
    def name(self) -> str:
        return self._srv_name

    @property
    def type(self):
        return self._srv_type

    @property
    def type_name(self) -> str:
        return self._srv_type._type

    @property
    def md5sum(self) -> str:
        return self._srv_type._md5sum

    @property
    def header(self) -> Dict[str, str]:
        return self._header

    async def close(self) -> None:
        await self._manager.unregister_service(self)
