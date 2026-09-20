from pydantic import BaseModel, EmailStr, Field, field_validator


class _EmailRequest(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def _lowercase_email(cls, value: EmailStr) -> str:
        return str(value).lower()


class RegisterRequest(_EmailRequest):
    password: str = Field(min_length=8, max_length=72)
    name: str | None = None


class LoginRequest(_EmailRequest):
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class UserResponse(BaseModel):
    id: str
    email: str
    name: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
