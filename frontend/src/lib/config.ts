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

  const base = API_BASE || window.location.origin
  const parsed = new URL(base, window.location.origin)
  const protocol = parsed.protocol === "https:" ? "wss:" : "ws:"
  const pathPrefix = parsed.pathname.replace(/\/$/, "")
  return `${protocol}//${parsed.host}${pathPrefix}${path}`
}
