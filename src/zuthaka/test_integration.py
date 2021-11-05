import pytest
from .backendapi.dtos import RequestDto, C2Dto, ListenerDto, LauncherDto
from .backendapi.dtos import ResponseDto
from .backendapi.services.ClassHandlers import Covenant
import logging
logger = logging.getLogger(__name__)

_handler = Covenant.CovenantC2

c2_dto = C2Dto(
    c2_type='covenant_integration',
    options={
        'url': 'https://127.0.0.1:7443',
        'username': 'pucara',
        'password': 'pucara'
        }
    )

listener_dto = ListenerDto(
    listener_type='default-http-profile',
    options={
        'connectAddresses': '127.0.0.1',
        'connectPort': '5555',
        'bindAdress': '127.0.0.1'
        }
    )

launcher_dto = LauncherDto(
    launcher_type='Powershell Launcher',
    options={
        'Delay': '1',
        }
    )

listener_internal_id = 0

false_c2_dto = C2Dto(c2_type='covenant_integration', options={
    'url': 'https://127.0.0.1:7443', 'username': 'false', 'password': 'false'})

invalid_c2_dto = C2Dto(c2_type='covenant_integration', options={
    'url': 'https://127.0.0.1:7443', 'username': 'false', 'password': 'false'})


@pytest.mark.asyncio
async def test_is_alive_invalid_c2():
    with pytest.raises(ConnectionError) as err:
        class_handler = _handler(invalid_c2_dto.options)
        dto = RequestDto(c2=invalid_c2_dto)
        await class_handler.is_alive(dto)


@pytest.mark.asyncio
async def test_is_alive_false_creds():
    with pytest.raises(ConnectionRefusedError) as err:
        class_handler = _handler(false_c2_dto.options)
        dto = RequestDto(c2=false_c2_dto)
        await class_handler.is_alive(dto)


@pytest.mark.asyncio
async def test_is_alive():
    class_handler = _handler(c2_dto.options)
    dto = RequestDto(c2=c2_dto)
    result = await class_handler.is_alive(dto)
    assert isinstance(result, ResponseDto)
    assert result.successful_transaction is True


@pytest.mark.asyncio
async def test_retrieve_agents():
    class_handler = _handler(c2_dto.options)
    dto = RequestDto(c2=c2_dto)
    result = await class_handler.retrieve_agents(dto)
    assert isinstance(result, ResponseDto)
    assert result.successful_transaction is True
    assert result.agents is not None
    assert isinstance(result.agents, list)


@pytest.mark.asyncio
async def test_create_listener():
    c2_handler = _handler(c2_dto.options)
    logger.debug('c2_handler: %r', c2_handler)

    listener_types = await c2_handler.get_listener_types()
    listener_handler = listener_types[listener_dto.listener_type]
    dto = RequestDto(c2=c2_dto, listener=listener_dto)
    result = await listener_handler.create_listener(listener_dto.options, dto)
    assert isinstance(result, ResponseDto)
    assert result.successful_transaction is True
    created_listener = result.created_listener
    assert created_listener.listener_internal_id is not None
    global listener_internal_id
    listener_internal_id = created_listener.listener_internal_id


@pytest.mark.asyncio
async def test_create_and_retrieve_launcher():
    c2_handler = _handler(c2_dto.options)
    logger.debug('c2_handler: %r', c2_handler)

    global listener_internal_id
    auxiliar_listener_dto = ListenerDto(
        listener_type='default-http-profile',
        options={
            'connectAddresses': '127.0.0.1',
            'connectPort': '5555',
            'bindAdress': '127.0.0.1'
            }
        )

    dto = RequestDto(c2=c2_dto, listener=auxiliar_listener_dto, launcher=launcher_dto)
    launcher_types = await c2_handler.get_launcher_types()
    launcher_handler = launcher_types[launcher_dto.launcher_type]

    response = await launcher_handler.create_and_retrieve_launcher(launcher_dto.options, dto)
    assert isinstance(response, ResponseDto)
    assert response.successful_transaction is True
    assert response.created_launcher is not None


@pytest.mark.asyncio
async def test_delete_listener():
    c2_handler = _handler(c2_dto.options)
    logger.debug('c2_handler: %r', c2_handler)

    listener_types = await c2_handler.get_listener_types()
    listener_handler = listener_types[listener_dto.listener_type]
    dto = RequestDto(c2=c2_dto, listener=listener_dto)
    global listener_internal_id
    response = await listener_handler.delete_listener(listener_internal_id, listener_dto.options, dto)
    assert isinstance(response, ResponseDto)
    assert response.successful_transaction is True