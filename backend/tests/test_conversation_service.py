from services.conversation_service import (
    DEFAULT_CONVERSATION_NAME,
    MAX_HISTORY_CHARS,
    MAX_HISTORY_MESSAGES,
    MAX_NAME_CHARS,
    ConversationService,
)


async def test_append_message_creates_named_conversation(db_session, create_user):
    await create_user(db_session, "u1")

    await ConversationService.append_message(
        db_session, "c1", "u1", "user", "  Plan   my trip  "
    )

    assert await ConversationService.conversation_exists(db_session, "c1", "u1")
    items, total = await ConversationService.list_conversations(
        db_session, "u1", limit=10, offset=0
    )
    assert total == 1
    assert items[0]["name"] == "Plan my trip"


async def test_conversation_name_truncates_and_falls_back(db_session, create_user):
    await create_user(db_session, "u1")

    await ConversationService.append_message(
        db_session, "c1", "u1", "user", "x" * (MAX_NAME_CHARS + 20)
    )
    await ConversationService.append_message(
        db_session, "c2", "u1", "assistant", "hello"
    )

    items, _ = await ConversationService.list_conversations(
        db_session, "u1", limit=10, offset=0
    )
    names = {item["id"]: item["name"] for item in items}
    assert names["c1"] == "x" * MAX_NAME_CHARS
    assert names["c2"] == DEFAULT_CONVERSATION_NAME


async def test_history_round_trips_in_order(db_session, create_user):
    await create_user(db_session, "u1")

    await ConversationService.append_message(db_session, "c1", "u1", "user", "hi")
    await ConversationService.append_message(
        db_session, "c1", "u1", "assistant", "hello"
    )

    history = await ConversationService.get_history(db_session, "c1")
    assert history == [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]


async def test_history_is_scoped_per_conversation(db_session, create_user):
    await create_user(db_session, "u1")

    await ConversationService.append_message(db_session, "c1", "u1", "user", "one")
    await ConversationService.append_message(db_session, "c2", "u1", "user", "two")

    assert await ConversationService.get_history(db_session, "c1") == [
        {"role": "user", "content": "one"}
    ]
    assert await ConversationService.get_history(db_session, "c2") == [
        {"role": "user", "content": "two"}
    ]


async def test_history_trims_to_message_limit(db_session, create_user):
    await create_user(db_session, "u1")

    for index in range(MAX_HISTORY_MESSAGES + 5):
        await ConversationService.append_message(
            db_session, "c1", "u1", "user", f"message-{index}"
        )

    history = await ConversationService.get_history(db_session, "c1")
    assert len(history) == MAX_HISTORY_MESSAGES
    assert history[-1]["content"] == f"message-{MAX_HISTORY_MESSAGES + 4}"


async def test_history_trims_to_char_budget(db_session, create_user):
    await create_user(db_session, "u1")

    for index in range(30):
        await ConversationService.append_message(
            db_session, "c1", "u1", "user", f"{index}-" + "x" * 400
        )

    history = await ConversationService.get_history(db_session, "c1")
    assert sum(len(message["content"]) for message in history) <= MAX_HISTORY_CHARS
    assert len(history) < 30
