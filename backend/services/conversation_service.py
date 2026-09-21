from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.conversation import Conversation
from models.message import ConversationMessage

MAX_HISTORY_MESSAGES = 20
MAX_HISTORY_CHARS = 6000
MAX_NAME_CHARS = 60
DEFAULT_CONVERSATION_NAME = "New conversation"


def _derive_name(content: str) -> str:
    name = " ".join(content.split()).strip()
    if not name:
        return DEFAULT_CONVERSATION_NAME
    return name[:MAX_NAME_CHARS].rstrip()


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
        conversation = await session.get(Conversation, conversation_id)
        if conversation is None:
            name = (
                _derive_name(content) if role == "user" else DEFAULT_CONVERSATION_NAME
            )
            session.add(Conversation(id=conversation_id, user_id=user_id, name=name))

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
    async def conversation_exists(
        session: AsyncSession,
        conversation_id: str,
        user_id: str,
    ) -> bool:
        result = await session.execute(
            select(Conversation.id).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
        return result.first() is not None

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

        Each row carries the conversation name plus its latest message and
        aggregate count derived from the linked messages.
        """
        ranked = select(
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
        ).subquery()

        rows = (
            (
                await session.execute(
                    select(
                        Conversation.id,
                        Conversation.name,
                        ranked.c.message_count,
                        ranked.c.last_message,
                        ranked.c.last_message_role,
                        ranked.c.created_at,
                        ranked.c.updated_at,
                    )
                    .join(ranked, ranked.c.id == Conversation.id)
                    .where(
                        Conversation.user_id == user_id,
                        ranked.c.rank == 1,
                    )
                    .order_by(ranked.c.updated_at.desc(), Conversation.id.desc())
                    .limit(limit)
                    .offset(offset)
                )
            )
            .mappings()
            .all()
        )

        total = (
            await session.execute(
                select(func.count())
                .select_from(Conversation)
                .where(Conversation.user_id == user_id)
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
