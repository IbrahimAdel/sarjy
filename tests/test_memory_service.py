from sqlalchemy import func, select

from models.preference import UserPreference
from services.memory_service import MemoryService


async def test_set_and_get_preference(db_session, create_user):
    await create_user(db_session, "u1")

    await MemoryService.set_user_preference(db_session, "u1", "city", "London")

    assert await MemoryService.get_user_preferences(db_session, "u1") == {
        "city": "London"
    }


async def test_set_preference_upserts_existing_key(db_session, create_user):
    await create_user(db_session, "u1")

    await MemoryService.set_user_preference(db_session, "u1", "city", "London")
    await MemoryService.set_user_preference(db_session, "u1", "city", "Paris")

    preferences = await MemoryService.get_user_preferences(db_session, "u1")
    assert preferences == {"city": "Paris"}

    count = (
        await db_session.execute(
            select(func.count())
            .select_from(UserPreference)
            .where(UserPreference.user_id == "u1")
        )
    ).scalar_one()
    assert count == 1


async def test_preferences_are_scoped_per_user(db_session, create_user):
    await create_user(db_session, "u1")
    await create_user(db_session, "u2")

    await MemoryService.set_user_preference(db_session, "u1", "city", "London")
    await MemoryService.set_user_preference(db_session, "u2", "city", "Paris")

    assert await MemoryService.get_user_preferences(db_session, "u1") == {
        "city": "London"
    }
    assert await MemoryService.get_user_preferences(db_session, "u2") == {
        "city": "Paris"
    }


async def test_get_preferences_unknown_user_is_empty(db_session):
    assert await MemoryService.get_user_preferences(db_session, "nobody") == {}
