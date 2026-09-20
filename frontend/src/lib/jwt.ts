import { jwtDecode } from "jwt-decode"

import type { SessionUser } from "@/types"

interface AccessTokenClaims {
  sub: string
  email?: string
  name?: string
  exp?: number
}

export function decodeAccessToken(token: string): SessionUser {
  const claims = jwtDecode<AccessTokenClaims>(token)
  return {
    id: claims.sub,
    email: claims.email ?? "",
    name: claims.name ?? claims.email ?? claims.sub,
    exp: claims.exp,
  }
}
