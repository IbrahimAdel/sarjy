import { act, render, screen, waitFor } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

const mocks = vi.hoisted(() => ({
  ensureAccessToken: vi.fn(async () => "token" as string | null),
}))

vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => ({ ensureAccessToken: mocks.ensureAccessToken }),
}))

import { useConversations } from "@/hooks/useConversations"

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  })
}

function summary(id: string) {
  return {
    id,
    name: `name-${id}`,
    message_count: 1,
    last_message: `msg-${id}`,
    last_message_role: "user" as const,
    created_at: "2026-01-01T00:00:00",
    updated_at: "2026-01-01T00:00:00",
  }
}

function Probe() {
  const { items, total, loading, loadMore } = useConversations()
  return (
    <div>
      <span data-testid="loading">{String(loading)}</span>
      <span data-testid="total">{total}</span>
      <ul>
        {items.map((item) => (
          <li key={item.id}>{item.id}</li>
        ))}
      </ul>
      <button type="button" onClick={loadMore}>
        more
      </button>
    </div>
  )
}

describe("useConversations", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.ensureAccessToken.mockResolvedValue("token")
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("loads the first page and appends the next one", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse({ items: [summary("c1")], total: 2, limit: 20, offset: 0 })
      )
      .mockResolvedValueOnce(
        jsonResponse({ items: [summary("c2")], total: 2, limit: 20, offset: 1 })
      )
    vi.stubGlobal("fetch", fetchMock)

    render(<Probe />)

    await waitFor(() =>
      expect(screen.getByTestId("loading")).toHaveTextContent("false")
    )
    expect(screen.getByText("c1")).toBeInTheDocument()
    expect(screen.getByTestId("total")).toHaveTextContent("2")

    await act(async () => {
      screen.getByRole("button", { name: "more" }).click()
    })

    await waitFor(() => expect(screen.getByText("c2")).toBeInTheDocument())
    expect(fetchMock).toHaveBeenLastCalledWith(
      "/conversations?limit=20&offset=1",
      expect.anything()
    )
  })

  it("refreshes and retries once after a 401", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse({ detail: "Invalid or expired token." }, 401)
      )
      .mockResolvedValueOnce(
        jsonResponse({ items: [summary("c1")], total: 1, limit: 20, offset: 0 })
      )
    vi.stubGlobal("fetch", fetchMock)

    render(<Probe />)

    await waitFor(() => expect(screen.getByText("c1")).toBeInTheDocument())
    expect(mocks.ensureAccessToken).toHaveBeenCalledWith(true)
  })
})
