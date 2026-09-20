import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react"

import { authApi } from "@/lib/api"
import { decodeAccessToken } from "@/lib/jwt"
import type { AuthTokens, RegisterPayload, SessionUser } from "@/types"

const REFRESH_STORAGE_KEY = "sarjy.refresh_token"

export type AuthStatus = "loading" | "anonymous" | "authenticated"

interface AuthContextValue {
  user: SessionUser | null
  status: AuthStatus
  login: (email: string, password: string) => Promise<void>
  register: (payload: RegisterPayload) => Promise<void>
  logout: () => void
  getAccessToken: () => string | null
  ensureAccessToken: (force?: boolean) => Promise<string | null>
  refresh: () => Promise<string | null>
}

const AuthContext = createContext<AuthContextValue | null>(null)

function readStoredRefreshToken(): string | null {
  if (typeof window === "undefined") {
    return null
  }
  return window.localStorage.getItem(REFRESH_STORAGE_KEY)
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<SessionUser | null>(null)
  const [status, setStatus] = useState<AuthStatus>("loading")
  const accessTokenRef = useRef<string | null>(null)
  const refreshTokenRef = useRef<string | null>(readStoredRefreshToken())

  const applyTokens = useCallback((tokens: AuthTokens) => {
    accessTokenRef.current = tokens.access_token
    refreshTokenRef.current = tokens.refresh_token
    window.localStorage.setItem(REFRESH_STORAGE_KEY, tokens.refresh_token)
    setUser(decodeAccessToken(tokens.access_token))
    setStatus("authenticated")
  }, [])

  const logout = useCallback(() => {
    accessTokenRef.current = null
    refreshTokenRef.current = null
    window.localStorage.removeItem(REFRESH_STORAGE_KEY)
    setUser(null)
    setStatus("anonymous")
  }, [])

  const refresh = useCallback(async (): Promise<string | null> => {
    const token = refreshTokenRef.current
    if (!token) {
      logout()
      return null
    }
    try {
      const tokens = await authApi.refresh(token)
      applyTokens(tokens)
      return tokens.access_token
    } catch {
      logout()
      return null
    }
  }, [applyTokens, logout])

  const login = useCallback(
    async (email: string, password: string) => {
      applyTokens(await authApi.login(email, password))
    },
    [applyTokens]
  )

  const ensureAccessToken = useCallback(
    async (force = false): Promise<string | null> => {
      const current = accessTokenRef.current
      if (!force && current !== null) {
        try {
          const { exp } = decodeAccessToken(current)
          if (exp === undefined || exp * 1000 - Date.now() > 10_000) {
            return current
          }
        } catch {
          // Malformed token; fall through to a refresh.
        }
      }
      return refresh()
    },
    [refresh]
  )

  const register = useCallback(
    async (payload: RegisterPayload) => {
      await authApi.register(payload)
      applyTokens(await authApi.login(payload.email, payload.password))
    },
    [applyTokens]
  )

  useEffect(() => {
    if (!refreshTokenRef.current) {
      setStatus("anonymous")
      return
    }
    void refresh()
  }, [refresh])

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      status,
      login,
      register,
      logout,
      refresh,
      ensureAccessToken,
      getAccessToken: () => accessTokenRef.current,
    }),
    [user, status, login, register, logout, refresh, ensureAccessToken]
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (context === null) {
    throw new Error("useAuth must be used within an AuthProvider")
  }
  return context
}
