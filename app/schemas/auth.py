from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.security import MAX_PASSWORD_BYTES


class LoginRequest(BaseModel):
    email: EmailStr
    # The upper bound is bcrypt's, not a policy — see core.security.
    password: str = Field(min_length=6, max_length=MAX_PASSWORD_BYTES)


class UserOut(BaseModel):
    """
    What the browser is allowed to know about a user.

    Explicit fields rather than the ORM object: `password_hash` is one
    forgotten exclusion away from being serialised into a JSON response.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    role: str
    is_active: bool
