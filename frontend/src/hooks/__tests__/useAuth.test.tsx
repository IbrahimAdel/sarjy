import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/api", () => ({
  ApiError: class ApiError extends Error {
    status = 0
  },
  authApi: {
    login: vi.fn(),
    refresh: vi.fn(),
    register: vi.fn(),
  },
}))

import { authApi } from "@/lib/api"
import { AuthProvider, useAuth } from "@/hooks/useAuth"
import { makeAccessToken } from "@/test/tokens"

const REFRESH_KEY = "sarjy.refresh_token"

function Probe() {
  const { status, user, login } = useAuth()
  return (
    <div>
      <span data-testid="status">{status}</span>
      <span data-testid="email">{user?.email ?? ""}</span>
      <button
        type="button"
        onClick={() => void login("a@example.com", "password123")}
      >
        login
      </button>
    </div>
  )
}

describe("useAuth", () => {
  beforeEach(() => {
    window.localStorage.clear()
    vi.mocked(authApi.login).mockReset()
    vi.mocked(authApi.refresh).mockReset()
  })

  it("starts anonymous without a stored refresh token", async () => {
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>
    )
    await waitFor(() =>
      expect(screen.getByTestId("status")).toHaveTextContent("anonymous")
    )
  })

  it("authenticates and persists the refresh token on login", async () => {
    vi.mocked(authApi.login).mockResolvedValue({
      access_token: makeAccessToken({
        sub: "u1",
        email: "a@example.com",
        name: "Ada",
      }),
      refresh_token: "refresh-1",
      token_type: "bearer",
    })
    const user = userEvent.setup()
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>
    )
    await waitFor(() =>
      expect(screen.getByTestId("status")).toHaveTextContent("anonymous")
    )

    await user.click(screen.getByRole("button", { name: "login" }))

    await waitFor(() =>
      expect(screen.getByTestId("status")).toHaveTextContent("authenticated")
    )
    expect(screen.getByTestId("email")).toHaveTextContent("a@example.com")
    expect(window.localStorage.getItem(REFRESH_KEY)).toBe("refresh-1")
  })

  it("rehydrates the session from a stored refresh token", async () => {
    window.localStorage.setItem(REFRESH_KEY, "stored")
    vi.mocked(authApi.refresh).mockResolvedValue({
      access_token: makeAccessToken({
        sub: "u2",
        email: "b@example.com",
        name: "Bob",
      }),
      refresh_token: "refresh-2",
      token_type: "bearer",
    })

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>
    )

    await waitFor(() =>
      expect(screen.getByTestId("status")).toHaveTextContent("authenticated")
    )
    expect(screen.getByTestId("email")).toHaveTextContent("b@example.com")
  })
})
