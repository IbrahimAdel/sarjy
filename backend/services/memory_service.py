from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from models.preference import UserPreference


class MemoryService:
    def __init__(self) -> None:
        msg = "MemoryService is a static-only helper and cannot be instantiated."
        raise TypeError(msg)

    @staticmethod
    async def get_user_preferences(
        session: AsyncSession, user_id: str
    ) -> dict[str, str]:
        prefs = (
            await session.execute(
                select(UserPreference.key, UserPreference.value).where(
                    UserPreference.user_id == user_id
                )
            )
        ).fetchall()
        return {row[0]: row[1] for row in prefs}

    @staticmethod
    async def _execute_upsert(
        session: AsyncSession, statement: Any, value: str
    ) -> None:
        await session.execute(
            statement.on_conflict_do_update(
                index_elements=["user_id", "key"],
                # Matches the model's naive datetime.now() columns.
                set_={"value": value, "updated_at": datetime.now()},  # noqa: DTZ005
            )
        )

    @staticmethod
    async def set_user_preference(
        session: AsyncSession,
        user_id: str,
        key: str,
        value: str,
    ) -> str:
        values = {"user_id": user_id, "key": key, "value": value}
        dialect = session.get_bind().dialect.name

        if dialect == "sqlite":
            await MemoryService._execute_upsert(
                session, sqlite_insert(UserPreference).values(**values), value
            )
        elif dialect == "postgresql":
            await MemoryService._execute_upsert(
                session, pg_insert(UserPreference).values(**values), value
            )
        else:
            # Fallback for dialects without a native upsert.
            preference = (
                await session.execute(
                    select(UserPreference).where(
                        UserPreference.user_id == user_id,
                        UserPreference.key == key,
                    )
                )
            ).scalar_one_or_none()
            if preference is None:
                session.add(UserPreference(key=key, value=value, user_id=user_id))
            else:
                preference.value = value

        await session.commit()
        return f"Saved: {key} = {value}"
