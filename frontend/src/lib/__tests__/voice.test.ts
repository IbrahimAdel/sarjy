import { describe, expect, it } from "vitest"

import { parseServerMessage } from "@/lib/voice"

describe("parseServerMessage", () => {
  it("parses status messages", () => {
    expect(parseServerMessage('{"event":"status","state":"thinking"}')).toEqual({
      event: "status",
      state: "thinking",
    })
  })

  it("parses transcript and text messages", () => {
    expect(
      parseServerMessage('{"event":"transcript_final","text":"hello"}')
    ).toEqual({ event: "transcript_final", text: "hello" })
    expect(parseServerMessage('{"event":"text_chunk","text":"hi"}')).toEqual({
      event: "text_chunk",
      text: "hi",
    })
  })

  it("parses errors with a default message", () => {
    expect(parseServerMessage('{"event":"error"}')).toEqual({
      event: "error",
      message: "Unknown error",
    })
  })

  it("rejects malformed or unknown payloads", () => {
    expect(parseServerMessage("{not json")).toBeNull()
    expect(parseServerMessage('{"event":"bogus"}')).toBeNull()
    expect(parseServerMessage('{"event":"status","state":"weird"}')).toBeNull()
  })
})
