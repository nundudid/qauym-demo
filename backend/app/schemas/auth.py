from pydantic import BaseModel, Field

from app.schemas.user import DisplayName, Email, Username


class RegisterIn(BaseModel):
    email: Email
    username: Username
    password: str = Field(min_length=8, max_length=128)
    display_name: DisplayName | None = None


class LoginIn(BaseModel):
    email: Email
    password: str = Field(min_length=1, max_length=128)
