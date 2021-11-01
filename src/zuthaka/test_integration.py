import asyncio
import pytest
from .backendapi.dtos import RequestDto, C2Dto
from .backendapi.services.ClassHandlers import Covenant
# from .backendapi.services.async_service import Service

service = Service.get_service()
covenant_dto = C2Dto(c2_type='covenant_integration', options={
    'url': 'http://127.0.0.1:7443', 'user': 'pucara', 'password': 'pucara'})
false_covenant_dto = C2Dto(c2_type='covenant_integration', options={
    'url': 'http://127.0.0.1:7443', 'user': 'false', 'password': 'false'})

@pytest.mark.parametrize("service, covenant_dto, expected", [
    (service, covenant_dto, True), (service, false_covenant_dto, False)])
@pytest.mark.asyncio
async def test_is_alive(service, covenant_dto, expected):
    class_handler = Covenant.CovenantC2(covenant_dto.options)
    assert await class_handler.is_alive()
