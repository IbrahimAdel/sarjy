import { useCallback, useEffect, useRef, useState } from "react"

import { useAuthedRequest } from "@/hooks/useAuthedRequest"
import { conversationsApi } from "@/lib/api"
import type { ConversationSummary } from "@/types"

export const CONVERSATIONS_PAGE_SIZE = 20

export interface ConversationsState {
  items: ConversationSummary[]
  total: number
  loading: boolean
  loadingMore: boolean
  error: string | null
  loadMore: () => void
  reload: () => Promise<void>
}

function errorMessage(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "Failed to load conversations."
}

export function useConversations(): ConversationsState {
  const send = useAuthedRequest()
  const [items, setItems] = useState<ConversationSummary[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const requestIdRef = useRef(0)

  const fetchPage = useCallback(
    (offset: number) =>
      send((token) =>
        conversationsApi.list(token, {
          limit: CONVERSATIONS_PAGE_SIZE,
          offset,
        })
      ),
    [send]
  )

  const reload = useCallback(async () => {
    const requestId = ++requestIdRef.current
    setLoading(true)
    setError(null)
    try {
      const page = await fetchPage(0)
      if (requestId !== requestIdRef.current) {
        return
      }
      setItems(page.items)
      setTotal(page.total)
    } catch (caught) {
      if (requestId === requestIdRef.current) {
        setError(errorMessage(caught))
      }
    } finally {
      if (requestId === requestIdRef.current) {
        setLoading(false)
      }
    }
  }, [fetchPage])

  const loadMore = useCallback(() => {
    void (async () => {
      setLoadingMore(true)
      setError(null)
      try {
        const page = await fetchPage(items.length)
        setItems((previous) => [...previous, ...page.items])
        setTotal(page.total)
      } catch (caught) {
        setError(errorMessage(caught))
      } finally {
        setLoadingMore(false)
      }
    })()
  }, [fetchPage, items.length])

  useEffect(() => {
    void reload()
  }, [reload])

  return {
    items,
    total,
    loading,
    loadingMore,
    error,
    loadMore,
    reload,
  }
}
