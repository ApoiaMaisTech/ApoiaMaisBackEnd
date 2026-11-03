"""O hash de senha (PBKDF2, ~80 ms de CPU) não pode rodar no event loop.

No event loop ele trava TODAS as requisições do processo: medido em
docs/PERFORMANCE.md (rota leve com p95 de 715 ms durante 10 logins).
"""
import asyncio
import threading
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.application.dto.create_user_request import CreateUserRequest
from app.application.dto.login_request import LoginRequest
from app.application.dto.update_user_request import UpdateUserRequest
from app.application.use_cases.auth.login_usecase import LoginUseCase
from app.application.use_cases.users.create_user_usecase import CreateUserUseCase
from app.application.use_cases.users.update_user_usecase import UpdateUserUseCase
from app.domain.entities.user import User
from app.domain.enums.user import UserRole

pytestmark = pytest.mark.asyncio


class RecordingPasswordService:
    def __init__(self):
        self.threads: list[threading.Thread] = []

    def hash(self, password: str) -> str:
        self.threads.append(threading.current_thread())
        return "salt$hash"

    def verify(self, password: str, password_hash: str) -> bool:
        self.threads.append(threading.current_thread())
        return True


def _user():
    return User(id=uuid4(), name="Ana", email="ana@example.com", password_hash="salt$hash", role=UserRole.STUDENT)


def _assert_off_loop(service: RecordingPasswordService):
    assert service.threads, "o serviço de senha não foi chamado"
    assert all(t is not threading.main_thread() for t in service.threads)


async def test_login_verifica_a_senha_fora_do_event_loop():
    service = RecordingPasswordService()
    repository = Mock(get_by_email=AsyncMock(return_value=_user()))
    jwt = Mock(generate_token=Mock(return_value="token"))

    await LoginUseCase(repository, service, jwt).execute(LoginRequest(email="ana@example.com", password="x"))

    _assert_off_loop(service)


async def test_criacao_gera_o_hash_fora_do_event_loop():
    service = RecordingPasswordService()
    def _create(user):
        user.id = uuid4()
        return user

    repository = Mock(get_by_email=AsyncMock(return_value=None), create=AsyncMock(side_effect=_create))

    await CreateUserUseCase(repository, service).execute(
        CreateUserRequest(name="Ana Maria", email="ana@example.com", password="senha-nova-123"), UserRole.STUDENT
    )

    _assert_off_loop(service)


async def test_atualizacao_gera_o_hash_fora_do_event_loop():
    service = RecordingPasswordService()
    user = _user()
    repository = Mock(
        get_by_id=AsyncMock(return_value=user),
        get_by_email=AsyncMock(return_value=None),
        update=AsyncMock(side_effect=lambda u: u),
    )

    await UpdateUserUseCase(repository, service).execute(
        user.id, UpdateUserRequest(email="ana@example.com", password="senha-nova-123")
    )

    _assert_off_loop(service)


async def test_logins_simultaneos_nao_travam_outra_tarefa():
    # com o hash no event loop, a tarefa leve só rodaria depois de todos os hashes
    from app.infrastructure.security.password import PasswordServiceImpl

    real = PasswordServiceImpl()
    password_hash = real.hash("senha-123")
    user = User(id=uuid4(), name="Ana", email="ana@example.com", password_hash=password_hash, role=UserRole.STUDENT)
    use_case = LoginUseCase(
        Mock(get_by_email=AsyncMock(return_value=user)), real, Mock(generate_token=Mock(return_value="t"))
    )

    ticks: list[float] = []

    async def heartbeat():
        loop = asyncio.get_running_loop()
        for _ in range(20):
            ticks.append(loop.time())
            await asyncio.sleep(0.005)

    await asyncio.gather(
        heartbeat(),
        *(use_case.execute(LoginRequest(email=user.email, password="senha-123")) for _ in range(6)),
    )

    gaps = [b - a for a, b in zip(ticks, ticks[1:])]
    # cada hash leva dezenas de ms; travando o loop, algum intervalo passaria de 100 ms
    assert max(gaps) < 0.1, f"event loop travou por {max(gaps) * 1000:.0f} ms"
