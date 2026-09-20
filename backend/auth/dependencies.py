from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from auth.security import AuthError, authenticate

bearer_scheme = HTTPBearer(auto_error=False)

UNAUTHORIZED_HEADERS = {"WWW-Authenticate": "Bearer"}


class AuthenticatedUser(BaseModel):
    user_id: str


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> AuthenticatedUser:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
            headers=UNAUTHORIZED_HEADERS,
        )
    try:
        user_id = authenticate(credentials.credentials)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers=UNAUTHORIZED_HEADERS,
        ) from exc
    return AuthenticatedUser(user_id=user_id)


CurrentUserDep = Annotated[AuthenticatedUser, Depends(get_current_user)]
