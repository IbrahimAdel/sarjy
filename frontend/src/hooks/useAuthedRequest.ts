import { useCallback } from "react"

import { useAuth } from "@/hooks/useAuth"
import { ApiError } from "@/lib/api"

/**
 * Runs an authenticated request with the current access token, refreshing
 * once and retrying if the server rejects the token with a 401.
 */
export function useAuthedRequest() {
  const { ensureAccessToken } = useAuth()

  return useCallback(
    async <T,>(fn: (token: string) => Promise<T>): Promise<T> => {
      const token = await ensureAccessToken()
      if (token === null) {
        throw new ApiError(401, "Your session expired. Please sign in again.")
      }

      try {
        return await fn(token)
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          const refreshed = await ensureAccessToken(true)
          if (refreshed !== null) {
            return await fn(refreshed)
          }
        }
        throw error
      }
    },
    [ensureAccessToken]
  )
}
