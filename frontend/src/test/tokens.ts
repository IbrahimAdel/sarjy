function base64Url(value: unknown): string {
  return btoa(JSON.stringify(value))
    .replace(/=/g, "")
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
}

export function makeAccessToken(
  claims: { sub: string; email?: string; name?: string; exp?: number } = {
    sub: "user-1",
    email: "a@example.com",
    name: "Ada",
    exp: Math.floor(Date.now() / 1000) + 900,
  }
): string {
  const header = base64Url({ alg: "RS256", typ: "JWT" })
  const payload = base64Url(claims)
  return `${header}.${payload}.signature`
}
