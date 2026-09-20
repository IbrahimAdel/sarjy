const CONVERSATION_STORAGE_KEY = "sarjy.conversation_id"

export function createConversationId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID()
  }
  return `conv-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

export function readActiveConversationId(): string | null {
  if (typeof window === "undefined") {
    return null
  }
  return window.localStorage.getItem(CONVERSATION_STORAGE_KEY)
}

export function storeActiveConversationId(id: string): void {
  if (typeof window === "undefined") {
    return
  }
  window.localStorage.setItem(CONVERSATION_STORAGE_KEY, id)
}

export function resolveActiveConversationId(): string {
  const existing = readActiveConversationId()
  if (existing) {
    return existing
  }
  const created = createConversationId()
  storeActiveConversationId(created)
  return created
}
