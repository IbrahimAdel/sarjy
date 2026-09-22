from collections.abc import AsyncIterator
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from settings import get_settings


def _async_database_url(url: str) -> str:
    if url.startswith("sqlite://"):
        return url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    return url


def _ensure_sqlite_directory(url: str) -> None:
    """SQLite does not create missing parent directories for file databases."""
    if not url.startswith("sqlite"):
        return
    database = make_url(_async_database_url(url)).database
    if not database or database == ":memory:":
        return
    Path(database).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


DATABASE_URL = _async_database_url(get_settings().database_url)
_ensure_sqlite_directory(get_settings().database_url)

engine = create_async_engine(
    DATABASE_URL,
    # SQLite is file-based; NullPool avoids connections leaking across event loops.
    poolclass=NullPool if DATABASE_URL.startswith("sqlite") else None,
)
if DATABASE_URL.startswith("sqlite"):

    @event.listens_for(engine.sync_engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, _record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session
