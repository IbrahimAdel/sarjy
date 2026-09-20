const rawApiUrl = import.meta.env.VITE_API_URL ?? ""
const rawWsUrl = import.meta.env.VITE_WS_URL ?? ""

export const API_BASE = rawApiUrl.replace(/\/+$/, "")
export const WS_BASE = rawWsUrl.replace(/\/+$/, "")

export function apiUrl(path: string): string {
  return `${API_BASE}${path}`
}

export function wsUrl(path: string): string {
  if (WS_BASE) {
    return `${WS_BASE}${path}`
  }

  const origin = API_BASE || window.location.origin
  const parsed = new URL(origin)
  const protocol = parsed.protocol === "https:" ? "wss:" : "ws:"
  return `${protocol}//${parsed.host}${path}`
}
