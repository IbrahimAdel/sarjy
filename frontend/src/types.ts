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
