import { afterEach, describe, expect, it, vi } from "vitest"

import { ApiError, authApi } from "@/lib/api"

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
