import { apiUrl } from "@/lib/config"
import type { AuthTokens, AuthUser, RegisterPayload } from "@/types"

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = "ApiError"
    this.status = status
  }
}

async function extractDetail(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json()
    if (
      body &&
      typeof body === "object" &&
      "detail" in body &&
      typeof body.detail === "string"
    ) {
      return body.detail
    }
  } catch {
    // Response had no JSON body; fall back to the status text.
  }
  return response.statusText || `Request failed (${response.status})`
}

async function request<T>(path: string, init: RequestInit): Promise<T> {
  const response = await fetch(apiUrl(path), {
    ...init,
    headers: {
      "content-type": "application/json",
      ...init.headers,
    },
  })

  if (!response.ok) {
    throw new ApiError(response.status, await extractDetail(response))
  }

  if (response.status === 204) {
    return undefined as T
  }
  return (await response.json()) as T
}

export const authApi = {
  register(payload: RegisterPayload): Promise<AuthUser> {
    return request<AuthUser>("/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    })
  },

  login(email: string, password: string): Promise<AuthTokens> {
    return request<AuthTokens>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    })
  },

  refresh(refreshToken: string): Promise<AuthTokens> {
    return request<AuthTokens>("/auth/refresh", {
      method: "POST",
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
  },
}
