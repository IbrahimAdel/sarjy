from types import SimpleNamespace

import pytest

from services import llm_service
from services.conversation_service import ConversationService
from services.llm_service import LLMEngine, _parse_tool_arguments
from services.memory_service import MemoryService


def _function(name=None, arguments=None):
    return SimpleNamespace(name=name, arguments=arguments)


def _tool_call(index, id=None, name=None, arguments=None):
    return SimpleNamespace(index=index, id=id, function=_function(name, arguments))


def _chunk(content=None, tool_calls=None):
    delta = SimpleNamespace(content=content, tool_calls=tool_calls)
    return SimpleNamespace(choices=[SimpleNamespace(delta=delta)])


class _FakeCompletions:
    def __init__(self, rounds):
        self.rounds = list(rounds)
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        chunks = self.rounds.pop(0)

        async def generate():
            for chunk in chunks:
                yield chunk

        return generate()


class _FakeClient:
    def __init__(self, rounds):
        self.chat = SimpleNamespace(completions=_FakeCompletions(rounds))


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, {}),
        ("", {}),
        ("not json", {}),
        ("[1, 2]", {}),
        ('{"key": "value"}', {"key": "value"}),
    ],
)
def test_parse_tool_arguments(raw, expected):
    assert _parse_tool_arguments(raw) == expected


async def test_system_prompt_instructs_proactive_saving(
    db_session, create_user, monkeypatch
):
    await create_user(db_session, "u1")
    await MemoryService.set_user_preference(db_session, "u1", "city", "London")

    client = _FakeClient([[_chunk(content="ok.")]])
    monkeypatch.setattr(llm_service, "get_openai_client", lambda: client)

    engine = LLMEngine(user_id="u1", conversation_id="c1")
    async for _ in engine.generate_response_stream(db_session, "I live in London"):
        pass

    system = client.chat.completions.calls[0]["messages"][0]
    assert system["role"] == "system"
    assert "save_preference" in system["content"]
    assert "immediately" in system["content"]
    assert "city=London" in system["content"]


async def test_direct_response_streams_and_persists(
    db_session, create_user, monkeypatch
):
    await create_user(db_session, "u1")
    client = _FakeClient([[_chunk(content="Hello "), _chunk(content="there.")]])
    monkeypatch.setattr(llm_service, "get_openai_client", lambda: client)

    engine = LLMEngine(user_id="u1", conversation_id="c1")
    collected = ""
    async for token in engine.generate_response_stream(db_session, "hi"):
        collected += token

    assert collected == "Hello there."
    assert len(client.chat.completions.calls) == 1

    history = await ConversationService.get_history(db_session, "c1")
    assert history == [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "Hello there."},
    ]


async def test_tool_loop_runs_concurrently_and_continues(
    db_session, create_user, monkeypatch
):
    await create_user(db_session, "u1")
    rounds = [
        [
            _chunk(tool_calls=[_tool_call(0, id="c1", arguments='{"key":')]),
            _chunk(
                tool_calls=[
                    _tool_call(0, arguments='"city","value":"London"}'),
                    _tool_call(1, id="c2", arguments='{"key":"units",'),
                ]
            ),
            _chunk(tool_calls=[_tool_call(1, arguments='"value":"metric"}')]),
        ],
        [_chunk(content="It "), _chunk(content="is sunny.")],
    ]
    rounds[0][0].choices[0].delta.tool_calls[0].function.name = "save_preference"
    rounds[0][1].choices[0].delta.tool_calls[1].function.name = "save_preference"

    client = _FakeClient(rounds)
    monkeypatch.setattr(llm_service, "get_openai_client", lambda: client)

    engine = LLMEngine(user_id="u1", conversation_id="c1")
    collected = ""
    async for token in engine.generate_response_stream(db_session, "save my city"):
        collected += token

    assert collected == "It is sunny."
    assert len(client.chat.completions.calls) == 2

    roles = [
        message["role"] for message in client.chat.completions.calls[1]["messages"]
    ]
    assert roles == ["system", "user", "assistant", "tool", "tool"]

    preferences = await MemoryService.get_user_preferences(db_session, "u1")
    assert preferences == {"city": "London", "units": "metric"}


async def test_unknown_tool_returns_not_found(db_session, create_user, monkeypatch):
    await create_user(db_session, "u1")
    rounds = [
        [_chunk(tool_calls=[_tool_call(0, id="c1", name="mystery", arguments="{}")])],
        [_chunk(content="Done.")],
    ]
    client = _FakeClient(rounds)
    monkeypatch.setattr(llm_service, "get_openai_client", lambda: client)

    engine = LLMEngine(user_id="u1", conversation_id="c1")
    async for _ in engine.generate_response_stream(db_session, "do a thing"):
        pass

    tool_messages = [
        message
        for message in client.chat.completions.calls[1]["messages"]
        if message["role"] == "tool"
    ]
    assert tool_messages[0]["content"] == "Tool not found."
