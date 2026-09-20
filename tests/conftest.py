import asyncio
import os
import tempfile

# Configure the environment before any application module is imported.
_TEST_DIR = tempfile.mkdtemp(prefix="sarjy-tests-")
os.environ["OPENAI_API_KEY"] = "sk-test-dummy"
os.environ["STT_ENABLED"] = "false"
os.environ["TTS_ENABLED"] = "false"
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DIR}/test.db"
os.environ["LOG_LEVEL"] = "WARNING"
os.environ["LOG_FORMAT"] = "text"

import pytest
from sqlalchemy import delete

from auth.security import hash_password
from database import AsyncSessionLocal, Base, engine
from models.message import ConversationMessage
from models.preference import UserPreference
from models.user import User

TEST_PASSWORD_HASH = hash_password("password123")


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    async def _create() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(_create())
    yield


@pytest.fixture
def create_user():
    async def _create(session, user_id: str) -> None:
        session.add(
            User(
                id=user_id,
                email=f"{user_id}@test.local",
                name=user_id,
                password=TEST_PASSWORD_HASH,
            )
        )
        await session.commit()

    return _create


@pytest.fixture
async def db_session():
    async with AsyncSessionLocal() as session:
        await session.execute(delete(ConversationMessage))
        await session.execute(delete(UserPreference))
        await session.execute(delete(User))
        await session.commit()
        yield session
