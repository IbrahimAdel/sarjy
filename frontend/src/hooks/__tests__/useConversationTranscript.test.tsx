import { act, render, screen, waitFor } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

const mocks = vi.hoisted(() => ({
  ensureAccessToken: vi.fn(async () => "token" as string | null),
}))

vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => ({ ensureAccessToken: mocks.ensureAccessToken }),
}))

import { useConversationTranscript } from "@/hooks/useConversationTranscript"

const TOTAL = 25

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  })
}

function makeMessage(index: number) {
  return {
    id: `m${index}`,
    conversation_id: "c1",
    role: index % 2 === 0 ? ("user" as const) : ("assistant" as const),
    content: `m${index}`,
    created_at: "2026-01-01T00:00:00",
  }
}

function Probe({ id }: { id: string }) {
  const { entries, hasMore, loadingEarlier, loadEarlier } =
    useConversationTranscript(id)
  return (
    <div>
      <span data-testid="count">{entries.length}</span>
      <span data-testid="first">{entries[0]?.text ?? ""}</span>
      <span data-testid="hasMore">{String(hasMore)}</span>
      <span data-testid="loadingEarlier">{String(loadingEarlier)}</span>
      <button type="button" onClick={loadEarlier}>
        earlier
      </button>
    </div>
  )
}

describe("useConversationTranscript", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.ensureAccessToken.mockResolvedValue("token")

    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = new URL(String(input), "http://localhost")
        const limit = Number(url.searchParams.get("limit"))
        const offset = Number(url.searchParams.get("offset"))
        const all = Array.from({ length: TOTAL }, (_, index) =>
          makeMessage(index)
        )
        return jsonResponse({
          items: all.slice(offset, offset + limit),
          total: TOTAL,
          limit,
          offset,
        })
      })
    )
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("opens on the most recent page and loads earlier messages", async () => {
    render(<Probe id="c1" />)

    await waitFor(() =>
      expect(screen.getByTestId("count")).toHaveTextContent("20")
    )
    expect(screen.getByTestId("first")).toHaveTextContent("m5")
    expect(screen.getByTestId("hasMore")).toHaveTextContent("true")

    await act(async () => {
      screen.getByRole("button", { name: "earlier" }).click()
    })

    await waitFor(() =>
      expect(screen.getByTestId("count")).toHaveTextContent("25")
    )
    expect(screen.getByTestId("first")).toHaveTextContent("m0")
    expect(screen.getByTestId("hasMore")).toHaveTextContent("false")
  })
})
