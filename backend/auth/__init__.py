from typing import Any

from auth.security import (
    AuthError,
    authenticate,
    build_jwks,
    create_access_token,
    create_refresh_token,
    decode_claims,
    decode_token,
    extract_token,
    hash_password,
    verify_password,
)

__all__ = [
    "AuthError",
    "authenticate",
    "build_jwks",
    "create_access_token",
    "create_refresh_token",
    "decode_claims",
    "decode_token",
    "extract_token",
    "hash_password",
    "load_public_jwks",
    "verify_password",
]


def load_public_jwks() -> dict[str, Any]:
    return build_jwks()
