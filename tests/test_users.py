import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from auth.security import hash_password
from models.message import ConversationMessage
from models.preference import UserPreference
from models.user import User
from services.conversation_service import ConversationService
from services.memory_service import MemoryService

TEST_PASSWORD_HASH = hash_password("password123")


async def _count(db_session, model, *criteria) -> int:
    result = await db_session.execute(
        select(func.count()).select_from(model).where(*criteria)
    )
    return result.scalar_one()


async def test_writes_reference_existing_user(db_session, create_user):
    await create_user(db_session, "u1")

    await MemoryService.set_user_preference(db_session, "u1", "city", "London")
    await ConversationService.append_message(db_session, "c1", "u1", "user", "hi")

    user_count = await _count(db_session, User, User.id == "u1")
    prefs = await _count(db_session, UserPreference, UserPreference.user_id == "u1")
    messages = await _count(
        db_session, ConversationMessage, ConversationMessage.user_id == "u1"
    )
    assert (user_count, prefs, messages) == (1, 1, 1)


async def test_deleting_user_cascades_to_children(db_session, create_user):
    await create_user(db_session, "u1")
    await MemoryService.set_user_preference(db_session, "u1", "city", "London")
    await ConversationService.append_message(db_session, "c1", "u1", "user", "hi")

    await db_session.execute(delete(User).where(User.id == "u1"))
    await db_session.commit()

    prefs = await _count(db_session, UserPreference, UserPreference.user_id == "u1")
    messages = await _count(
        db_session, ConversationMessage, ConversationMessage.user_id == "u1"
    )
    assert (prefs, messages) == (0, 0)


async def test_email_is_unique(db_session):
    db_session.add(
        User(
            id="a",
            email="dup@example.com",
            name="A",
            password=TEST_PASSWORD_HASH,
        )
    )
    await db_session.commit()

    with pytest.raises(IntegrityError):
        db_session.add(
            User(
                id="b",
                email="dup@example.com",
                name="B",
                password=TEST_PASSWORD_HASH,
            )
        )
        await db_session.commit()
    await db_session.rollback()


async def test_foreign_key_is_enforced(db_session):
    with pytest.raises(IntegrityError):
        db_session.add(UserPreference(user_id="ghost", key="k", value="v"))
        await db_session.commit()
    await db_session.rollback()
