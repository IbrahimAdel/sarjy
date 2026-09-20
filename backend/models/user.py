from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from util import gen_uuid


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(), primary_key=True, default=gen_uuid)
    email: Mapped[str] = mapped_column(String(), unique=True, index=True)
    name: Mapped[str] = mapped_column(String())
    password: Mapped[str] = mapped_column(String())

    created_at: Mapped[datetime] = mapped_column(
        DateTime(), default=datetime.now, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(), default=datetime.now, onupdate=datetime.now
    )
