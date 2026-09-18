from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from util import gen_uuid


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=gen_uuid)
    conversation_id: Mapped[str] = mapped_column(String(), index=True)
    user_id: Mapped[str] = mapped_column(
        String(), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(), index=True)
    content: Mapped[str] = mapped_column(Text(), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(), default=datetime.now, index=True
    )
