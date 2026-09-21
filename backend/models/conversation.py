from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from util import gen_uuid


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(
        String(), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(), default=datetime.now, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(), default=datetime.now, onupdate=datetime.now
    )
