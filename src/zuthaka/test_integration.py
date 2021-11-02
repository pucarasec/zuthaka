import asyncio
import pytest
from .backendapi.dtos import RequestDto, C2Dto, ListenerDto
from .backendapi.services.ClassHandlers import Covenant
import logging
logger = logging.getLogger(__name__)

covenant_dto = C2Dto(c2_type='covenant_integration', options={
    'url': 'https://127.0.0.1:7443', 'username': 'pucara', 'password': 'pucara'})

listener_dto = ListenerDto(listener_type='default-http-profile', options={
    'connectAddresses': '127.0.0.1', 'connectPort': '4444', 'bindAdress': '127.0.0.1'})

# false_covenant_dto = C2Dto(c2_type='covenant_integration', options={
#     'url': 'https://127.0.0.1:7443', 'username': 'false', 'password': 'false'})
# @pytest.mark.parametrize(" covenant_dto, expected", [
#   ( covenant_dto, True), ( false_covenant_dto, False)])
# async def test_is_alive( covenant_dto, expected):
@pytest.mark.asyncio
async def test_is_alive():
    class_handler = Covenant.CovenantC2(covenant_dto.options)
    dto = RequestDto(c2=covenant_dto)
    assert await class_handler.is_alive(dto)

@pytest.mark.asyncio
async def test_create_and_delete_listener():
    c2_handler = Covenant.CovenantC2(covenant_dto.options)
    logger.debug('c2_handler: ', c2_handler)
    listener_handler = Covenant.CovenantHTTPListenerType(c2_handler, listener_dto.options)
    dto = RequestDto(c2=covenant_dto, listener=listener_dto)
    created_listener = await listener_handler.create_listener(listener_dto.options, dto)
    assert hasattr(created_listener, 'listener_internal_id')
    response = await listener_handler.delete_listener(listener_dto.options, created_listener.get('listener_internal_id'), listener_dto.options, dto)
    assert not response