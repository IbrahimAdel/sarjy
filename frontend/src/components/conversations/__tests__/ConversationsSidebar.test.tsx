import { fireEvent, render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"

import { ConversationsSidebar } from "@/components/conversations/ConversationsSidebar"
import type { ConversationSummary } from "@/types"

const summary: ConversationSummary = {
  id: "c1",
  message_count: 2,
  last_message: "hello there",
  last_message_role: "assistant",
  created_at: "2026-01-01T00:00:00",
  updated_at: "2026-01-01T00:00:00",
}

function renderSidebar(
  overrides: Partial<Parameters<typeof ConversationsSidebar>[0]> = {}
) {
  const props = {
    items: [summary],
    total: 1,
    activeId: "c1",
    loading: false,
    loadingMore: false,
    error: null,
    open: true,
    onSelect: vi.fn(),
    onNew: vi.fn(),
    onLoadMore: vi.fn(),
    onReload: vi.fn(),
    onClose: vi.fn(),
    ...overrides,
  }
  render(<ConversationsSidebar {...props} />)
  return props
}

describe("ConversationsSidebar", () => {
  it("renders conversations and reports selection", () => {
    const props = renderSidebar()

    expect(screen.getByText("hello there")).toBeInTheDocument()
    fireEvent.click(screen.getByText("hello there"))

    expect(props.onSelect).toHaveBeenCalledWith("c1")
  })

  it("shows a load more button while more pages remain", () => {
    const props = renderSidebar({ total: 5 })

    fireEvent.click(screen.getByRole("button", { name: /load more/i }))
    expect(props.onLoadMore).toHaveBeenCalled()
  })

  it("renders the empty state when there are no conversations", () => {
    renderSidebar({ items: [], total: 0 })

    expect(screen.getByText(/no conversations yet/i)).toBeInTheDocument()
    expect(
      screen.queryByRole("button", { name: /load more/i })
    ).not.toBeInTheDocument()
  })
})
