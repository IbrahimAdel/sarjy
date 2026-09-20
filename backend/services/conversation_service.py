from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.message import ConversationMessage

MAX_HISTORY_MESSAGES = 20
MAX_HISTORY_CHARS = 6000


class ConversationService:
    def __init__(self) -> None:
        msg = "ConversationService is a static-only helper and cannot be instantiated."
        raise TypeError(msg)

    @staticmethod
    async def append_message(
        session: AsyncSession,
        conversation_id: str,
        user_id: str,
        role: str,
        content: str,
    ) -> None:
        session.add(
            ConversationMessage(
                conversation_id=conversation_id,
                user_id=user_id,
                role=role,
                content=content,
            )
        )
        await session.commit()

    @staticmethod
    async def get_history(
        session: AsyncSession,
        conversation_id: str,
        *,
        max_messages: int = MAX_HISTORY_MESSAGES,
        max_chars: int = MAX_HISTORY_CHARS,
    ) -> list[dict[str, str]]:
        """Recent turns, oldest-first, trimmed to a character budget."""
        rows = (
            await session.execute(
                select(ConversationMessage.role, ConversationMessage.content)
                .where(ConversationMessage.conversation_id == conversation_id)
                .order_by(
                    ConversationMessage.created_at.desc(),
                    ConversationMessage.id.desc(),
                )
                .limit(max_messages)
            )
        ).fetchall()

        history = [{"role": row[0], "content": row[1]} for row in reversed(rows)]

        total_chars = sum(len(message["content"]) for message in history)
        while history and total_chars > max_chars:
            total_chars -= len(history[0]["content"])
            history.pop(0)

        return history

    @staticmethod
    async def list_conversations(
        session: AsyncSession,
        user_id: str,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[dict[str, Any]], int]:
        """Conversations for a user, most recently updated first.

        A conversation is derived from its messages; the row carries the
        latest message plus aggregate count and timestamps.
        """
        ranked = (
            select(
                ConversationMessage.conversation_id.label("id"),
                ConversationMessage.content.label("last_message"),
                ConversationMessage.role.label("last_message_role"),
                ConversationMessage.created_at.label("updated_at"),
                func.count()
                .over(partition_by=ConversationMessage.conversation_id)
                .label("message_count"),
                func.min(ConversationMessage.created_at)
                .over(partition_by=ConversationMessage.conversation_id)
                .label("created_at"),
                func.row_number()
                .over(
                    partition_by=ConversationMessage.conversation_id,
                    order_by=(
                        ConversationMessage.created_at.desc(),
                        ConversationMessage.id.desc(),
                    ),
                )
                .label("rank"),
            )
            .where(ConversationMessage.user_id == user_id)
            .subquery()
        )

        rows = (
            (
                await session.execute(
                    select(
                        ranked.c.id,
                        ranked.c.message_count,
                        ranked.c.last_message,
                        ranked.c.last_message_role,
                        ranked.c.created_at,
                        ranked.c.updated_at,
                    )
                    .where(ranked.c.rank == 1)
                    .order_by(ranked.c.updated_at.desc(), ranked.c.id.desc())
                    .limit(limit)
                    .offset(offset)
                )
            )
            .mappings()
            .all()
        )

        total = (
            await session.execute(
                select(
                    func.count(func.distinct(ConversationMessage.conversation_id))
                ).where(ConversationMessage.user_id == user_id)
            )
        ).scalar_one()

        return [dict(row) for row in rows], total

    @staticmethod
    async def list_messages(
        session: AsyncSession,
        conversation_id: str,
        user_id: str,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[ConversationMessage], int]:
        """Messages in a conversation, oldest first, scoped to the owner."""
        filters = (
            ConversationMessage.conversation_id == conversation_id,
            ConversationMessage.user_id == user_id,
        )

        total = (
            await session.execute(
                select(func.count()).select_from(ConversationMessage).where(*filters)
            )
        ).scalar_one()

        rows = (
            (
                await session.execute(
                    select(ConversationMessage)
                    .where(*filters)
                    .order_by(
                        ConversationMessage.created_at.asc(),
                        ConversationMessage.id.asc(),
                    )
                    .limit(limit)
                    .offset(offset)
                )
            )
            .scalars()
            .all()
        )

        return list(rows), total
