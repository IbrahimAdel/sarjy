from sqlalchemy import select
from sqlalchemy.orm import Session

from models.message import ConversationMessage

MAX_HISTORY_MESSAGES = 20
MAX_HISTORY_CHARS = 6000


class ConversationService:
    def __init__(self) -> None:
        msg = "ConversationService is a static-only helper and cannot be instantiated."
        raise TypeError(msg)

    @staticmethod
    def append_message(
        session: Session,
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
        session.commit()

    @staticmethod
    def get_history(
        session: Session,
        conversation_id: str,
        *,
        max_messages: int = MAX_HISTORY_MESSAGES,
        max_chars: int = MAX_HISTORY_CHARS,
    ) -> list[dict[str, str]]:
        """Recent turns, oldest-first, trimmed to a character budget."""
        rows = session.execute(
            select(ConversationMessage.role, ConversationMessage.content)
            .where(ConversationMessage.conversation_id == conversation_id)
            .order_by(
                ConversationMessage.created_at.desc(),
                ConversationMessage.id.desc(),
            )
            .limit(max_messages)
        ).fetchall()

        history = [{"role": row[0], "content": row[1]} for row in reversed(rows)]

        total_chars = sum(len(message["content"]) for message in history)
        while history and total_chars > max_chars:
            total_chars -= len(history[0]["content"])
            history.pop(0)

        return history
