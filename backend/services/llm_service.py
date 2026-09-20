import asyncio
import json
from collections.abc import AsyncGenerator
from functools import lru_cache
from typing import Any

from openai import AsyncOpenAI
from openai.types.chat import (
    ChatCompletionToolParam,
)
from sqlalchemy.ext.asyncio import AsyncSession

from services.conversation_service import ConversationService
from services.memory_service import MemoryService
from settings import get_settings
from tools.weather import (
    MEMORY_TOOL_SPEC,
    WEATHER_TOOL_SPEC,
    WeatherService,
)

MAX_TOOL_ROUNDS = 4


@lru_cache
def get_openai_client() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=get_settings().require_openai_api_key())


def _parse_tool_arguments(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


class LLMEngine:
    user_id: str
    conversation_id: str

    def __init__(self, user_id: str, conversation_id: str) -> None:
        self.user_id = user_id
        self.conversation_id = conversation_id
        # An AsyncSession cannot be used concurrently; serialise DB tools.
        self._db_lock = asyncio.Lock()

    async def _execute_tool(
        self, session: AsyncSession, name: str, args: dict[str, Any]
    ) -> str:
        if name == "get_weather":
            try:
                return await WeatherService.get_current_weather(
                    float(args["latitude"]),
                    float(args["longitude"]),
                    str(args["city_name"]),
                )
            except (KeyError, TypeError, ValueError) as exc:
                return f"Could not fetch weather: invalid arguments ({exc})."

        if name == "save_preference":
            try:
                async with self._db_lock:
                    return str(
                        await MemoryService.set_user_preference(
                            session,
                            self.user_id,
                            str(args["key"]),
                            str(args["value"]),
                        )
                    )
            except (KeyError, TypeError, ValueError) as exc:
                return f"Could not save preference: invalid arguments ({exc})."

        return "Tool not found."

    async def _build_messages(
        self, session: AsyncSession, user_transcript: str
    ) -> list[dict[str, Any]]:
        await ConversationService.append_message(
            session,
            self.conversation_id,
            self.user_id,
            "user",
            user_transcript,
        )
        history = await ConversationService.get_history(
            session, self.conversation_id
        )
        preferences = await MemoryService.get_user_preferences(session, self.user_id)

        system_prompt = (
            "You are Sarjy, an upbeat voice assistant. Keep answers brief, spoken "
            "and conversational; avoid markdown, lists and emoji.\n"
            f"User Known Preferences context: {json.dumps(preferences)}"
        )
        return [{"role": "system", "content": system_prompt}, *history]

    async def generate_response_stream(
        self, session: AsyncSession, user_transcript: str
    ) -> AsyncGenerator[str]:
        settings = get_settings()
        client = get_openai_client()

        messages = await self._build_messages(session, user_transcript)
        tools: list[ChatCompletionToolParam] = [  # pyright: ignore[reportAssignmentType]
            WEATHER_TOOL_SPEC,
            MEMORY_TOOL_SPEC,
        ]

        answer_parts: list[str] = []

        for _ in range(MAX_TOOL_ROUNDS):
            stream = await client.chat.completions.create(  # pyright: ignore[reportCallIssue]
                model=settings.openai_model,
                messages=messages,  # pyright: ignore[reportArgumentType]
                tools=tools,
                tool_choice="auto",
                stream=True,
            )

            round_content: list[str] = []
            pending_calls: dict[int, dict[str, str]] = {}

            async for chunk in stream:
                delta = chunk.choices[0].delta

                if delta.content:
                    round_content.append(delta.content)
                    answer_parts.append(delta.content)
                    yield delta.content

                for call in delta.tool_calls or []:  # pyright: ignore[reportAttributeAccessIssue]
                    entry = pending_calls.setdefault(
                        call.index,  # pyright: ignore[reportAttributeAccessIssue]
                        {"id": "", "name": "", "arguments": ""},
                    )
                    if call.id:  # pyright: ignore[reportAttributeAccessIssue]
                        entry["id"] = call.id  # pyright: ignore[reportAttributeAccessIssue]
                    function = call.function  # pyright: ignore[reportAttributeAccessIssue]
                    if function is not None:
                        if function.name:
                            entry["name"] += function.name
                        if function.arguments:
                            entry["arguments"] += function.arguments

            if not pending_calls:
                break

            ordered = [pending_calls[index] for index in sorted(pending_calls)]
            messages.append(
                {
                    "role": "assistant",
                    "content": "".join(round_content) or None,
                    "tool_calls": [
                        {
                            "id": call["id"],
                            "type": "function",
                            "function": {
                                "name": call["name"],
                                "arguments": call["arguments"],
                            },
                        }
                        for call in ordered
                    ],
                }
            )

            results = await asyncio.gather(
                *[
                    self._execute_tool(
                        session,
                        call["name"],
                        _parse_tool_arguments(call["arguments"]),
                    )
                    for call in ordered
                ]
            )

            for call, result in zip(ordered, results, strict=True):
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call["id"],
                        "content": result,
                    }
                )

        final_answer = "".join(answer_parts).strip()
        if final_answer:
            await ConversationService.append_message(
                session,
                self.conversation_id,
                self.user_id,
                "assistant",
                final_answer,
            )
