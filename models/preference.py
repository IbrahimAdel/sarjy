from datetime import datetime

from sqlalchemy import DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from util import gen_uuid


class UserPreference(Base):
    __tablename__ = "user_preferences"
    __table_args__ = (UniqueConstraint("user_id", "key"),)

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(String(), index=True)

    key: Mapped[str] = mapped_column(String(), index=True)
    value: Mapped[str] = mapped_column(String(), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(), default=datetime.now, onupdate=datetime.now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(), default=datetime.now, onupdate=datetime.now
    )
