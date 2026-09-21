export interface AuthTokens {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface AuthUser {
  id: string
  email: string
  name: string
}

export interface SessionUser extends AuthUser {
  exp?: number
}

export interface RegisterPayload {
  email: string
  password: string
  name?: string
}

export type AssistantState = "listening" | "thinking" | "speaking" | "idle"

export type VoicePhase = "idle" | "connecting" | "live" | "error"

export type EntryRole = "user" | "assistant"

export interface ConversationEntry {
  id: string
  role: EntryRole
  text: string
}

export interface Page<T> {
  items: T[]
  total: number
  limit: number
  offset: number
}

export interface ConversationSummary {
  id: string
  name: string
  message_count: number
  last_message: string
  last_message_role: EntryRole
  created_at: string
  updated_at: string
}

export interface ConversationMessage {
  id: string
  conversation_id: string
  role: EntryRole
  content: string
  created_at: string
}
