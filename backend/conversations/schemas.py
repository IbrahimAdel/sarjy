from datetime import datetime

from pydantic import BaseModel, ConfigDict


class Page[T](BaseModel):
    items: list[T]
    total: int
    limit: int
    offset: int


class ConversationSummary(BaseModel):
    id: str
    name: str
    message_count: int
    last_message: str
    last_message_role: str
    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    role: str
    content: str
    created_at: datetime
