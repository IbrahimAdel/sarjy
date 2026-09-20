import { useCallback, useEffect, useRef, useState } from "react"
import { toast } from "sonner"

import { useAuth } from "@/hooks/useAuth"
import { useMicCapture } from "@/hooks/useMicCapture"
import { usePcmPlayer } from "@/hooks/usePcmPlayer"
import { wsUrl } from "@/lib/config"
import { parseServerMessage } from "@/lib/voice"
import type { AssistantState, ConversationEntry, EntryRole, VoicePhase } from "@/types"

const CONVERSATION_STORAGE_KEY = "sarjy.conversation_id"

let entryCounter = 0

function nextEntryId(): string {
  entryCounter += 1
  return `entry-${entryCounter}`
}

function resolveConversationId(): string {
  const existing = window.localStorage.getItem(CONVERSATION_STORAGE_KEY)
  if (existing) {
    return existing
  }
  const created =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID()
      : `conv-${Date.now()}-${Math.random().toString(16).slice(2)}`
  window.localStorage.setItem(CONVERSATION_STORAGE_KEY, created)
  return created
}

export function useVoiceConversation() {
  const { refresh, ensureAccessToken } = useAuth()
  const mic = useMicCapture()
  const player = usePcmPlayer()

  const [phase, setPhase] = useState<VoicePhase>("idle")
  const [connected, setConnected] = useState(false)
  const [assistantState, setAssistantState] = useState<AssistantState>("idle")
  const [entries, setEntries] = useState<ConversationEntry[]>([])
  const [partial, setPartial] = useState("")

  const socketRef = useRef<WebSocket | null>(null)
  const assistantEntryRef = useRef<string | null>(null)
  const connectRef = useRef<
    (allowRetry: boolean, forceRefresh?: boolean) => Promise<void>
  >(async () => undefined)
  const micRef = useRef(mic)
  const playerRef = useRef(player)

  const appendEntry = useCallback((role: EntryRole, text: string) => {
    setEntries((previous) => [...previous, { id: nextEntryId(), role, text }])
  }, [])

  const appendAssistantChunk = useCallback((text: string) => {
    setEntries((previous) => {
      const currentId = assistantEntryRef.current
      const last = previous.at(-1)
      if (currentId !== null && last?.id === currentId) {
        const updated = { ...last, text: last.text + text }
        return [...previous.slice(0, -1), updated]
      }
      const id = nextEntryId()
      assistantEntryRef.current = id
      return [...previous, { id, role: "assistant", text }]
    })
  }, [])

  const teardown = useCallback(() => {
    mic.stop()
    player.stop()
    setConnected(false)
    setAssistantState("idle")
    setPartial("")
  }, [mic, player])

  const connect = useCallback(
    async (allowRetry: boolean, forceRefresh = false): Promise<void> => {
      setPhase("connecting")

      // Create and resume the audio contexts synchronously, while still inside
      // the click handler. Autoplay policies reject contexts resumed later.
      player.prime()
      mic.prime()

      let token: string | null = null
      try {
        token = forceRefresh ? await refresh() : await ensureAccessToken()
      } catch {
        token = null
      }
      if (token === null) {
        toast.error("Your session expired. Please sign in again.")
        setPhase("error")
        return
      }

      // Never let audio setup block the websocket; playback starts when ready.
      await Promise.race([
        player.resume().catch(() => undefined),
        new Promise((resolve) => setTimeout(resolve, 1500)),
      ])

      const conversationId = resolveConversationId()
      let socket: WebSocket
      try {
        socket = new WebSocket(
          wsUrl(
            `/ws/audio?token=${encodeURIComponent(token)}&conversation_id=${encodeURIComponent(conversationId)}`
          )
        )
      } catch (error) {
        toast.error("Could not open the voice connection.", {
          description: error instanceof Error ? error.message : String(error),
        })
        setPhase("error")
        return
      }
      socket.binaryType = "arraybuffer"
      socketRef.current = socket

      socket.onmessage = (event: MessageEvent<string | ArrayBuffer>) => {
        if (typeof event.data !== "string") {
          player.push(event.data)
          return
        }
        const message = parseServerMessage(event.data)
        if (message === null) {
          return
        }
        switch (message.event) {
          case "status":
            setAssistantState(message.state)
            break
          case "transcript_partial":
            setPartial(message.text)
            break
          case "transcript_final":
            setPartial("")
            assistantEntryRef.current = null
            appendEntry("user", message.text)
            break
          case "text_chunk":
            appendAssistantChunk(message.text)
            break
          case "error":
            toast.error(message.message)
            break
        }
      }

      socket.onopen = () => {
        setConnected(true)
        setPhase("live")
        socket.send(
          JSON.stringify({ event: "start", conversation_id: conversationId })
        )
        mic
          .start((frame) => {
            if (socket.readyState === WebSocket.OPEN) {
              socket.send(frame)
            }
          })
          .catch((error: unknown) => {
            toast.error("Microphone unavailable", {
              description: error instanceof Error ? error.message : String(error),
            })
            setPhase("error")
          })
      }

      socket.onerror = () => {
        toast.error("Voice connection failed.")
      }

      socket.onclose = (event: CloseEvent) => {
        socketRef.current = null
        teardown()
        if (event.code === 1008 && allowRetry) {
          void connectRef.current(false, true)
          return
        }
        setPhase("idle")
      }
    },
    [
      appendAssistantChunk,
      appendEntry,
      ensureAccessToken,
      mic,
      player,
      refresh,
      teardown,
    ]
  )

  useEffect(() => {
    connectRef.current = connect
  }, [connect])

  const start = useCallback(() => {
    const socket = socketRef.current
    if (
      socket !== null &&
      (socket.readyState === WebSocket.OPEN ||
        socket.readyState === WebSocket.CONNECTING)
    ) {
      return
    }
    socketRef.current = null
    void connect(true)
  }, [connect])

  const stop = useCallback(() => {
    const socket = socketRef.current
    socketRef.current = null
    if (socket !== null) {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ event: "stop" }))
      }
      socket.close(1000)
    }
    teardown()
    setPhase("idle")
  }, [teardown])

  const sendText = useCallback((text: string) => {
    const socket = socketRef.current
    if (socket === null || socket.readyState !== WebSocket.OPEN) {
      return false
    }
    socket.send(JSON.stringify({ event: "user_transcript", text }))
    return true
  }, [])

  useEffect(() => {
    micRef.current = mic
    playerRef.current = player
  }, [mic, player])

  useEffect(() => {
    return () => {
      socketRef.current?.close(1000)
      socketRef.current = null
      micRef.current.stop()
      playerRef.current.stop()
    }
  }, [])

  return {
    phase,
    connected,
    assistantState,
    entries,
    partial,
    start,
    stop,
    sendText,
  }
}
