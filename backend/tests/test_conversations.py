from fastapi.testclient import TestClient

import main
from services.conversation_service import ConversationService

PASSWORD = "password123"


def _auth_header(client: TestClient, email: str) -> dict[str, str]:
    client.post("/auth/register", json={"email": email, "password": PASSWORD})
    tokens = client.post(
        "/auth/login", json={"email": email, "password": PASSWORD}
    ).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_conversations_require_auth():
    with TestClient(main.app) as client:
        assert client.get("/conversations").status_code == 401
        assert client.get("/conversations/c1/messages").status_code == 401


def test_conversations_reject_invalid_token():
    with TestClient(main.app) as client:
        response = client.get(
            "/conversations", headers={"Authorization": "Bearer not-a-token"}
        )

    assert response.status_code == 401


def test_conversations_empty_page():
    with TestClient(main.app) as client:
        headers = _auth_header(client, "conv-empty@example.com")
        response = client.get("/conversations", headers=headers)

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "limit": 20, "offset": 0}


def test_messages_unknown_conversation_returns_404():
    with TestClient(main.app) as client:
        headers = _auth_header(client, "conv-404@example.com")
        response = client.get("/conversations/missing/messages", headers=headers)

    assert response.status_code == 404


def test_conversations_validate_pagination_params():
    with TestClient(main.app) as client:
        headers = _auth_header(client, "conv-validate@example.com")
        assert client.get("/conversations?limit=0", headers=headers).status_code == 422
        assert (
            client.get("/conversations?limit=101", headers=headers).status_code == 422
        )
        assert (
            client.get("/conversations?offset=-1", headers=headers).status_code == 422
        )


async def test_list_conversations_aggregates_and_orders(db_session, create_user):
    await create_user(db_session, "u1")
    await ConversationService.append_message(db_session, "c1", "u1", "user", "first")
    await ConversationService.append_message(
        db_session, "c1", "u1", "assistant", "second"
    )
    await ConversationService.append_message(db_session, "c2", "u1", "user", "other")

    items, total = await ConversationService.list_conversations(
        db_session, "u1", limit=10, offset=0
    )

    assert total == 2
    assert items[0]["id"] == "c2"
    c1 = next(item for item in items if item["id"] == "c1")
    assert c1["message_count"] == 2
    assert c1["last_message"] == "second"
    assert c1["last_message_role"] == "assistant"


async def test_list_conversations_paginates(db_session, create_user):
    await create_user(db_session, "u1")
    for index in range(5):
        await ConversationService.append_message(
            db_session, f"c{index}", "u1", "user", f"m{index}"
        )

    first, total = await ConversationService.list_conversations(
        db_session, "u1", limit=2, offset=0
    )
    second, _ = await ConversationService.list_conversations(
        db_session, "u1", limit=2, offset=2
    )

    assert total == 5
    assert len(first) == 2
    assert len(second) == 2
    assert {item["id"] for item in first}.isdisjoint({item["id"] for item in second})


async def test_list_messages_paginates_in_order(db_session, create_user):
    await create_user(db_session, "u1")
    for index in range(3):
        await ConversationService.append_message(
            db_session, "c1", "u1", "user", f"m{index}"
        )

    first, total = await ConversationService.list_messages(
        db_session, "c1", "u1", limit=2, offset=0
    )
    second, _ = await ConversationService.list_messages(
        db_session, "c1", "u1", limit=2, offset=2
    )

    assert total == 3
    assert [message.content for message in first] == ["m0", "m1"]
    assert [message.content for message in second] == ["m2"]


async def test_list_messages_scoped_to_owner(db_session, create_user):
    await create_user(db_session, "u1")
    await create_user(db_session, "u2")
    await ConversationService.append_message(db_session, "c1", "u1", "user", "mine")
    await ConversationService.append_message(db_session, "c1", "u2", "user", "theirs")

    items, total = await ConversationService.list_messages(
        db_session, "c1", "u1", limit=10, offset=0
    )

    assert total == 1
    assert [message.content for message in items] == ["mine"]
