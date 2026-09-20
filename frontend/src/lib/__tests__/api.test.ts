import { afterEach, describe, expect, it, vi } from "vitest"

import { ApiError, authApi, conversationsApi } from "@/lib/api"

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  })
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe("authApi", () => {
  it("posts login credentials and returns tokens", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(
        jsonResponse({ access_token: "a", refresh_token: "r", token_type: "bearer" })
      )
    vi.stubGlobal("fetch", fetchMock)

    const tokens = await authApi.login("User@Example.com", "password123")

    expect(tokens.access_token).toBe("a")
    expect(fetchMock).toHaveBeenCalledWith(
      "/auth/login",
      expect.objectContaining({ method: "POST" })
    )
  })

  it("throws an ApiError with the server detail", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse({ detail: "Invalid credentials." }, 401))
    )

    await expect(authApi.login("a@b.com", "nope")).rejects.toMatchObject({
      name: "ApiError",
      status: 401,
      message: "Invalid credentials.",
    })
    await expect(authApi.login("a@b.com", "nope")).rejects.toBeInstanceOf(ApiError)
  })
})

describe("conversationsApi", () => {
  it("lists conversations with a bearer token and pagination", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        items: [
          {
            id: "c1",
            message_count: 2,
            last_message: "hello",
            last_message_role: "assistant",
            created_at: "2026-01-01T00:00:00",
            updated_at: "2026-01-01T00:00:05",
          },
        ],
        total: 1,
        limit: 20,
        offset: 0,
      })
    )
    vi.stubGlobal("fetch", fetchMock)

    const page = await conversationsApi.list("token-123", {
      limit: 20,
      offset: 40,
    })

    expect(page.items[0]?.id).toBe("c1")
    expect(fetchMock).toHaveBeenCalledWith(
      "/conversations?limit=20&offset=40",
      expect.objectContaining({
        headers: expect.objectContaining({
          authorization: "Bearer token-123",
        }),
      })
    )
  })

  it("loads messages for an encoded conversation id", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(
        jsonResponse({ items: [], total: 0, limit: 20, offset: 0 })
      )
    vi.stubGlobal("fetch", fetchMock)

    await conversationsApi.messages("token-123", "c 1/2", {
      limit: 20,
      offset: 0,
    })

    expect(fetchMock).toHaveBeenCalledWith(
      "/conversations/c%201%2F2/messages?limit=20&offset=0",
      expect.anything()
    )
  })
})
