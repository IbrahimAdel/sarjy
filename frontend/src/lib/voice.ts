import type { AssistantState } from "@/types"

export type ServerMessage =
  | { event: "status"; state: AssistantState }
  | { event: "transcript_partial"; text: string }
  | { event: "transcript_final"; text: string }
  | { event: "text_chunk"; text: string }
  | { event: "error"; message: string }

const ASSISTANT_STATES: readonly AssistantState[] = [
  "listening",
  "thinking",
  "speaking",
  "idle",
]

function isAssistantState(value: unknown): value is AssistantState {
  return (
    typeof value === "string" &&
    (ASSISTANT_STATES as readonly string[]).includes(value)
  )
}

export function parseServerMessage(raw: string): ServerMessage | null {
  let payload: unknown
  try {
    payload = JSON.parse(raw)
  } catch {
    return null
  }

  if (!payload || typeof payload !== "object" || !("event" in payload)) {
    return null
  }

  const record = payload as Record<string, unknown>
  switch (record.event) {
    case "status":
      return isAssistantState(record.state)
        ? { event: "status", state: record.state }
        : null
    case "transcript_partial":
    case "transcript_final":
    case "text_chunk":
      return typeof record.text === "string"
        ? { event: record.event, text: record.text }
        : null
    case "error":
      return { event: "error", message: String(record.message ?? "Unknown error") }
    default:
      return null
  }
}
