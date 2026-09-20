import json
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

import bcrypt
from fastapi import WebSocket
from joserfc import jwt
from joserfc.errors import JoseError
from joserfc.jwk import RSAKey
from joserfc.jwt import JWTClaimsRegistry

from settings import get_settings
from util import gen_uuid

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"

BCRYPT_ROUNDS = 12

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class AuthError(Exception):
    """Raised when a credential or token cannot be authenticated."""


def _jwks_path() -> Path:
    path = Path(get_settings().auth_jwks_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def _load_key_parameters() -> dict[str, Any]:
    raw: dict[str, Any] = json.loads(_jwks_path().read_text(encoding="utf-8"))
    keys = raw.get("keys") or []
    if not keys:
        msg = "No signing keys configured in JWKS."
        raise AuthError(msg)
    return keys[0]


@lru_cache
def get_signing_key() -> RSAKey:
    return RSAKey.import_key(_load_key_parameters())


@lru_cache
def get_verification_key() -> RSAKey:
    return RSAKey.import_key(get_signing_key().as_dict(private=False))


@lru_cache
def get_claims_registry() -> JWTClaimsRegistry:
    settings = get_settings()
    return JWTClaimsRegistry(
        iss={"essential": True, "value": settings.auth_issuer},
        aud={"essential": True, "value": settings.auth_audience},
        exp={"essential": True},
    )


def build_jwks() -> dict[str, Any]:
    raw: dict[str, Any] = json.loads(_jwks_path().read_text(encoding="utf-8"))
    keys = raw.get("keys") or []
    public_keys = [RSAKey.import_key(key).as_dict(private=False) for key in keys]
    return {"keys": public_keys}


def hash_password(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    ).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def _create_token(subject: str, token_type: str, ttl_seconds: int) -> str:
    settings = get_settings()
    now = int(time.time())
    claims = {
        "sub": subject,
        "iss": settings.auth_issuer,
        "aud": settings.auth_audience,
        "iat": now,
        "exp": now + ttl_seconds,
        "type": token_type,
        "jti": gen_uuid(),
    }
    return jwt.encode({"alg": settings.auth_algorithm}, claims, get_signing_key())


def create_access_token(subject: str) -> str:
    return _create_token(
        subject, ACCESS_TOKEN_TYPE, get_settings().access_token_ttl_seconds
    )


def create_refresh_token(subject: str) -> str:
    return _create_token(
        subject, REFRESH_TOKEN_TYPE, get_settings().refresh_token_ttl_seconds
    )


def decode_token(token: str, expected_type: str | None = None) -> str:
    settings = get_settings()
    try:
        decoded = jwt.decode(
            token,
            get_verification_key(),
            algorithms=[settings.auth_algorithm],
        )
        get_claims_registry().validate(decoded.claims)
    except (JoseError, ValueError) as exc:
        msg = "Invalid token."
        raise AuthError(msg) from exc

    if expected_type is not None and decoded.claims.get("type") != expected_type:
        msg = "Unexpected token type."
        raise AuthError(msg)

    subject = decoded.claims.get("sub")
    if not isinstance(subject, str) or not subject:
        msg = "Token missing subject."
        raise AuthError(msg)
    return subject


def authenticate(token: str) -> str:
    return decode_token(token, ACCESS_TOKEN_TYPE)


def extract_token(websocket: WebSocket) -> str | None:
    header = websocket.headers.get("authorization")
    if header:
        scheme, _, credentials = header.partition(" ")
        if scheme.lower() == "bearer" and credentials:
            return credentials
        return None
    return websocket.query_params.get("token") or None
