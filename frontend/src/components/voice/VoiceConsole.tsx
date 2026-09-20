import { useState, type FormEvent } from "react"
import { Loader2, Mic, MicOff, SendHorizontal } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { StatusBadge } from "@/components/voice/StatusBadge"
import { TranscriptList } from "@/components/voice/TranscriptList"
import { useVoiceConversation } from "@/hooks/useVoiceConversation"

export function VoiceConsole() {
  const {
    phase,
    connected,
    assistantState,
    entries,
    partial,
    start,
    stop,
    sendText,
  } = useVoiceConversation()
  const [draft, setDraft] = useState("")

  const isConnecting = phase === "connecting" && !connected

  const handleToggle = () => {
    if (connected) {
      stop()
    } else if (!isConnecting) {
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
    <Card className="flex h-[calc(100vh-8rem)] flex-col">
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

      <CardContent className="flex-1 overflow-y-auto py-4">
        <TranscriptList entries={entries} partial={partial} />
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
