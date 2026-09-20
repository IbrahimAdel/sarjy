import { describe, expect, it } from "vitest"

import { decodeAccessToken } from "@/lib/jwt"
import { makeAccessToken } from "@/test/tokens"

describe("decodeAccessToken", () => {
  it("maps sub/email/name into a session user", () => {
    const token = makeAccessToken({
      sub: "abc",
      email: "user@example.com",
      name: "User",
      exp: 123,
    })

    expect(decodeAccessToken(token)).toEqual({
      id: "abc",
      email: "user@example.com",
      name: "User",
      exp: 123,
    })
  })

  it("falls back to email then sub when name is missing", () => {
    const token = makeAccessToken({ sub: "abc", email: "user@example.com" })
    expect(decodeAccessToken(token).name).toBe("user@example.com")
  })
})
