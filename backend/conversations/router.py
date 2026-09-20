from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from auth.dependencies import CurrentUserDep
from conversations.schemas import ConversationSummary, MessageResponse, Page
from database import get_session
from services.conversation_service import ConversationService

router = APIRouter(prefix="/conversations", tags=["conversations"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]
LimitQuery = Annotated[int, Query(ge=1, le=100)]
OffsetQuery = Annotated[int, Query(ge=0)]

CONVERSATION_NOT_FOUND = "Conversation not found."


@router.get("", response_model=Page[ConversationSummary])
async def list_conversations(
    current_user: CurrentUserDep,
    session: SessionDep,
    limit: LimitQuery = 20,
    offset: OffsetQuery = 0,
) -> Page[ConversationSummary]:
    items, total = await ConversationService.list_conversations(
        session,
        current_user.user_id,
        limit=limit,
        offset=offset,
    )
    return Page[ConversationSummary](
        items=[ConversationSummary.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{conversation_id}/messages", response_model=Page[MessageResponse])
async def list_messages(
    conversation_id: str,
    current_user: CurrentUserDep,
    session: SessionDep,
    limit: LimitQuery = 20,
    offset: OffsetQuery = 0,
) -> Page[MessageResponse]:
    messages, total = await ConversationService.list_messages(
        session,
        conversation_id,
        current_user.user_id,
        limit=limit,
        offset=offset,
    )
    if total == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=CONVERSATION_NOT_FOUND)

    return Page[MessageResponse](
        items=[MessageResponse.model_validate(message) for message in messages],
        total=total,
        limit=limit,
        offset=offset,
    )
