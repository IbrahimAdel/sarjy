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
from sqlalchemy import text

import models.message
import models.preference  # noqa: F401
from database import AsyncSessionLocal, Base, engine


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    async def _create() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(_create())
    yield


@pytest.fixture
async def db_session():
    async with AsyncSessionLocal() as session:
        await session.execute(text("DELETE FROM user_preferences"))
        await session.execute(text("DELETE FROM conversation_messages"))
        await session.commit()
        yield session
