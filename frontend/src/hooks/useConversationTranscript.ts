import { useCallback, useEffect, useRef, useState } from "react"

import { useAuthedRequest } from "@/hooks/useAuthedRequest"
import { conversationsApi } from "@/lib/api"
import type { ConversationEntry, ConversationMessage } from "@/types"

export const TRANSCRIPT_PAGE_SIZE = 20

export interface TranscriptState {
  entries: ConversationEntry[]
  hasMore: boolean
  loading: boolean
  loadingEarlier: boolean
  error: string | null
  loadEarlier: () => void
  reload: () => Promise<void>
}

function toEntry(message: ConversationMessage): ConversationEntry {
  return { id: message.id, role: message.role, text: message.content }
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Failed to load messages."
}

/**
 * Loads a conversation's messages, starting at the most recent page so the
 * transcript opens at the bottom. Older pages are prepended via loadEarlier.
 */
export function useConversationTranscript(
  conversationId: string
): TranscriptState {
  const send = useAuthedRequest()
  const [entries, setEntries] = useState<ConversationEntry[]>([])
  const [hasMore, setHasMore] = useState(false)
  const [loading, setLoading] = useState(true)
  const [loadingEarlier, setLoadingEarlier] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const offsetRef = useRef(0)
  const requestIdRef = useRef(0)

  const reload = useCallback(async () => {
    const requestId = ++requestIdRef.current
    setLoading(true)
    setError(null)
    try {
      const probe = await send((token) =>
        conversationsApi.messages(token, conversationId, {
          limit: 1,
          offset: 0,
        })
      )
      const total = probe.total
      if (total === 0) {
        if (requestId === requestIdRef.current) {
          setEntries([])
          offsetRef.current = 0
          setHasMore(false)
        }
        return
      }

      const offset = Math.max(0, total - TRANSCRIPT_PAGE_SIZE)
      const page = await send((token) =>
        conversationsApi.messages(token, conversationId, {
          limit: TRANSCRIPT_PAGE_SIZE,
          offset,
        })
      )
      if (requestId !== requestIdRef.current) {
        return
      }
      setEntries(page.items.map(toEntry))
      offsetRef.current = offset
      setHasMore(offset > 0)
    } catch (caught) {
      if (requestId === requestIdRef.current) {
        setError(errorMessage(caught))
      }
    } finally {
      if (requestId === requestIdRef.current) {
        setLoading(false)
      }
    }
  }, [conversationId, send])

  const loadEarlier = useCallback(() => {
    const currentOffset = offsetRef.current
    if (currentOffset <= 0) {
      setHasMore(false)
      return
    }
    const nextOffset = Math.max(0, currentOffset - TRANSCRIPT_PAGE_SIZE)
    const limit = currentOffset - nextOffset

    void (async () => {
      setLoadingEarlier(true)
      setError(null)
      try {
        const page = await send((token) =>
          conversationsApi.messages(token, conversationId, {
            limit,
            offset: nextOffset,
          })
        )
        setEntries((previous) => [...page.items.map(toEntry), ...previous])
        offsetRef.current = nextOffset
        setHasMore(nextOffset > 0)
      } catch (caught) {
        setError(errorMessage(caught))
      } finally {
        setLoadingEarlier(false)
      }
    })()
  }, [conversationId, send])

  useEffect(() => {
    setEntries([])
    offsetRef.current = 0
    setHasMore(false)
    void reload()
  }, [reload])

  return {
    entries,
    hasMore,
    loading,
    loadingEarlier,
    error,
    loadEarlier,
    reload,
  }
}
