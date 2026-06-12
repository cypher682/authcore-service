import asyncio
import itertools
import os
import uuid

import pytest
import redis
from httpx import ASGITransport, AsyncClient
from sqlalchemy import update

from app.db.database import AsyncSessionLocal
from app.main import app
from app.models.user import User


_client_counter = itertools.count(10)
REDIS_URL = os.environ["REDIS_URL"]


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def unique_email() -> str:
    return f"test-{uuid.uuid4().hex}@example.com"


@pytest.fixture
def strong_password() -> str:
    return "StrongerPass123!"


@pytest.fixture
async def client():
    client_octet = next(_client_counter)
    transport = ASGITransport(app=app, client=(f"10.20.0.{client_octet}", 1234))
    async with AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clear_login_lockout_keys():
    _clear_login_keys()
    yield
    _clear_login_keys()


def _clear_login_keys() -> None:
    redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    keys = redis_client.keys("authcore:login:*")
    if keys:
        redis_client.delete(*keys)
    redis_client.close()


async def make_superuser(email: str) -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(User).where(User.email == email).values(is_superuser=True)
        )
        await session.commit()
