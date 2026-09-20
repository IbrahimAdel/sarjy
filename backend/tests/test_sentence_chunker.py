from collections.abc import AsyncIterator

from main import _stream_sentences


async def _chunks(tokens: list[str]) -> list[str]:
    async def source() -> AsyncIterator[str]:
        for token in tokens:
            yield token

    return [chunk async for chunk in _stream_sentences(source())]


async def test_flushes_on_sentence_boundary():
    assert await _chunks(["Hello ", "world. ", "This is a longer", " sentence!"]) == [
        "Hello world. ",
        "This is a longer sentence!",
    ]


async def test_trailing_fragment_is_flushed():
    assert await _chunks(["no punctuation here"]) == ["no punctuation here"]


async def test_short_sentence_is_flushed_at_end():
    assert await _chunks(["Hi"]) == ["Hi"]


async def test_no_empty_chunk_for_empty_stream():
    assert await _chunks([]) == []
