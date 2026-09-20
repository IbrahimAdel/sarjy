import { useEffect, useRef, useState, type FormEvent } from "react"
import { Loader2, Mic, MicOff, SendHorizontal } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { StatusBadge } from "@/components/voice/StatusBadge"
import { TranscriptList } from "@/components/voice/TranscriptList"
import { useConversationTranscript } from "@/hooks/useConversationTranscript"
import { useVoiceConversation } from "@/hooks/useVoiceConversation"

interface VoiceConsoleProps {
  conversationId: string
  onSessionEnd?: () => void
}

export function VoiceConsole({
  conversationId,
  onSessionEnd,
}: VoiceConsoleProps) {
  const {
    phase,
    connected,
    assistantState,
    entries,
    partial,
    start,
    stop,
    sendText,
  } = useVoiceConversation(conversationId)
  const transcript = useConversationTranscript(conversationId)
  const [draft, setDraft] = useState("")

  const previouslyConnected = useRef(false)

  useEffect(() => {
    if (previouslyConnected.current && !connected) {
      onSessionEnd?.()
    }
    previouslyConnected.current = connected
  }, [connected, onSessionEnd])

  const isConnecting = phase === "connecting" && !connected

  const handleToggle = () => {
    if (connected) {
      stop()
    } else if (!isConnecting) {
      void transcript.reload()
      start()
    }
  }

  const handleSend = (event: FormEvent) => {
    event.preventDefault()
    const text = draft.trim()
    if (text && sendText(text)) {
      setDraft("")
    }
  }

  return (
    <Card className="flex h-full min-h-0 flex-col">
      <CardHeader className="flex-row items-center justify-between gap-2 border-b">
        <div className="flex items-center gap-2">
          <StatusBadge state={assistantState} />
          {phase === "error" ? (
            <span className="text-sm text-destructive">
              Connection error. Try again.
            </span>
          ) : null}
        </div>
        <Button
          type="button"
          onClick={handleToggle}
          disabled={isConnecting}
          variant={connected ? "destructive" : "default"}
        >
          {isConnecting ? (
            <Loader2 className="animate-spin" aria-hidden="true" />
          ) : connected ? (
            <MicOff aria-hidden="true" />
          ) : (
            <Mic aria-hidden="true" />
          )}
          {isConnecting ? "Connecting..." : connected ? "Stop" : "Start talking"}
        </Button>
      </CardHeader>

      <CardContent className="min-h-0 flex-1 overflow-y-auto py-4">
        {transcript.hasMore ? (
          <div className="mb-3 flex justify-center">
            <Button
              type="button"
              size="sm"
              variant="ghost"
              onClick={transcript.loadEarlier}
              disabled={transcript.loadingEarlier}
            >
              {transcript.loadingEarlier ? (
                <Loader2 className="animate-spin" aria-hidden="true" />
              ) : null}
              Load earlier messages
            </Button>
          </div>
        ) : null}
        <TranscriptList
          entries={[...transcript.entries, ...entries]}
          partial={partial}
        />
      </CardContent>

      <form
        onSubmit={handleSend}
        className="flex items-center gap-2 border-t p-3"
      >
        <Input
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder={
            connected ? "Type a message instead..." : "Start a session to chat"
          }
          disabled={!connected}
          aria-label="Message"
        />
        <Button
          type="submit"
          size="icon"
          disabled={!connected || !draft.trim()}
        >
          <SendHorizontal aria-hidden="true" />
          <span className="sr-only">Send</span>
        </Button>
      </form>
    </Card>
  )
}
