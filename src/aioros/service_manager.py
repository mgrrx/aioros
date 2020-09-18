from typing import Callable
from typing import Dict
from typing import List
from typing import Optional
from typing import TypeVar

from .api.master_api_client import MasterApiClient
from .api.master_api_client import MasterApiClientError
from .tcpros.client import Client
from .tcpros.client import create_client
from .tcpros.service import Service

SrvType = TypeVar('SrvType')
SrvTypeRequest = TypeVar('SrvTypeRequest')
SrvTypeResponse = TypeVar('SrvTypeResponse')


class ServiceDoesNotExist(Exception):
    pass


class ServiceManager:

    def __init__(self, master_api_client: MasterApiClient) -> None:
        self._master_api_client = master_api_client
        self._clients: List[Client] = []
        self._services: Dict[str, Service] = {}

    async def close(self) -> None:
        for client in self._clients:
            await client.close()
        self._clients.clear()

        for service in list(self._services.values()):
            await self.unregister_service(service)

    async def unregister_service(self, service: Service) -> None:
        if service.name in self._services:
            del self._services[service.name]
            await self._master_api_client.unregister_service(service.name)

    def __contains__(self, service_name: str) -> bool:
        return service_name in self._services

    def get(self, service_name: str) -> Optional[Service]:
        return self._services.get(service_name)

    async def create_service(
        self,
        node_name: str,
        srv_name: str,
        srv_type: SrvType,
        callback: Callable[[SrvTypeRequest], SrvTypeResponse]
    ) -> Service:
        if srv_name in self._services:
            raise ValueError(f'service {srv_name} is already registered')

        await self._master_api_client.register_service(srv_name)
        service = Service(self, node_name, srv_name, srv_type, callback)
        self._services[srv_name] = service
        return service

    async def create_client(
        self,
        node_name: str,
        srv_name: str,
        srv_type: SrvType,
        *,
        persistent: bool = False
    ) -> Client:
        try:
            tcpros_uri = await self._master_api_client.lookup_service(srv_name)
        except MasterApiClientError:
            raise ServiceDoesNotExist(srv_name)
        client = create_client(node_name, srv_name, srv_type, tcpros_uri,
                               persistent)
        self._clients.append(client)
        return client
