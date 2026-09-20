import { useEffect, useRef } from "react"

import { cn } from "@/lib/utils"
import type { ConversationEntry } from "@/types"

function Bubble({
  role,
  text,
  pending,
}: {
  role: ConversationEntry["role"]
  text: string
  pending?: boolean
}) {
  const isUser = role === "user"
  return (
    <div className={cn("flex", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[80%] rounded-2xl px-3.5 py-2 text-sm whitespace-pre-wrap",
          isUser
            ? "bg-primary text-primary-foreground"
            : "bg-muted text-foreground",
          pending && "opacity-70"
        )}
      >
        {text}
      </div>
    </div>
  )
}

export function TranscriptList({
  entries,
  partial,
}: {
  entries: ConversationEntry[]
  partial: string
}) {
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" })
  }, [entries, partial])

  if (entries.length === 0 && !partial) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
        Press start and say something to begin.
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-3">
      {entries.map((entry) => (
        <Bubble key={entry.id} role={entry.role} text={entry.text} />
      ))}
      {partial ? <Bubble role="user" text={partial} pending /> : null}
      <div ref={endRef} />
    </div>
  )
}
