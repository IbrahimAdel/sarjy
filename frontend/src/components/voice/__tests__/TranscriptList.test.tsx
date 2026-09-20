import { render } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { TranscriptList } from "@/components/voice/TranscriptList"
import type { ConversationEntry } from "@/types"

let scrollIntoView: ReturnType<typeof vi.fn>

beforeEach(() => {
  scrollIntoView = vi.fn()
  Element.prototype.scrollIntoView =
    scrollIntoView as unknown as Element["scrollIntoView"]
})

afterEach(() => {
  delete (Element.prototype as { scrollIntoView?: unknown }).scrollIntoView
})

function entry(id: string): ConversationEntry {
  return { id, role: "user", text: id }
}

describe("TranscriptList scrolling", () => {
  it("does not scroll when older messages are prepended", () => {
    const view = render(
      <TranscriptList entries={[entry("c")]} partial="" />
    )
    expect(scrollIntoView).toHaveBeenCalledTimes(1)

    scrollIntoView.mockClear()
    view.rerender(
      <TranscriptList
        entries={[entry("a"), entry("b"), entry("c")]}
        partial=""
      />
    )

    expect(scrollIntoView).not.toHaveBeenCalled()
  })

  it("scrolls to the bottom when a new message arrives", () => {
    const view = render(
      <TranscriptList entries={[entry("a")]} partial="" />
    )
    scrollIntoView.mockClear()

    view.rerender(
      <TranscriptList entries={[entry("a"), entry("b")]} partial="" />
    )

    expect(scrollIntoView).toHaveBeenCalledTimes(1)
  })

  it("scrolls to the bottom when a partial transcript updates", () => {
    const view = render(<TranscriptList entries={[entry("a")]} partial="" />)
    scrollIntoView.mockClear()

    view.rerender(<TranscriptList entries={[entry("a")]} partial="hel" />)

    expect(scrollIntoView).toHaveBeenCalledTimes(1)
  })

  it("does not scroll when re-rendered without transcript changes", () => {
    const view = render(<TranscriptList entries={[entry("a")]} partial="" />)
    scrollIntoView.mockClear()

    // Simulates a parent re-render (e.g. loadingEarlier toggling) that
    // recreates the entries array with identical contents.
    view.rerender(<TranscriptList entries={[entry("a")]} partial="" />)

    expect(scrollIntoView).not.toHaveBeenCalled()
  })
})
