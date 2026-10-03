from fastapi import APIRouter, HTTPException, Response, status

from app.api.deps import CurrentUser, SessionDep
from app.core.config import settings
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    verify_password,
)
from app.repositories import user as user_repo
from app.schemas.auth import LoginRequest, UserOut

router = APIRouter()


@router.post("/login", response_model=UserOut)
async def login(payload: LoginRequest, response: Response, db: SessionDep) -> object:
    """
    Exchange credentials for a session cookie.

    The token is set as an httpOnly cookie rather than returned in the body:
    a body the frontend has to store ends up in localStorage, where any script
    on the page can read it.
    """
    user = await user_repo.get_by_email(db, payload.email)

    # Hash a password even when the account doesn't exist. Short-circuiting
    # here answers "no such user" in microseconds and "wrong password" in
    # ~200ms, and that gap is enough to enumerate who holds an account.
    password_ok = verify_password(
        payload.password,
        user.password_hash if user else DUMMY_PASSWORD_HASH,
    )

    # One message for all three failures. "No such email" tells an attacker
    # which addresses to keep guessing against.
    if user is None or not password_ok or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    response.set_cookie(
        key=settings.AUTH_COOKIE_NAME,
        value=create_access_token(user.id, user.role),
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        # Lax, not Strict: Strict withholds the cookie on any cross-site
        # navigation, so following a link to the panel from email lands the
        # user on the login screen despite an active session.
        samesite="lax",
        secure=settings.COOKIE_SECURE,
        path="/",
    )
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> None:
    """
    Clear the session cookie.

    ponytail: the JWT stays cryptographically valid until it expires — this
    drops the browser's copy, it does not revoke the token. Add a denylist (or
    a per-user token version column) when "log out everywhere" becomes a
    requirement.
    """
    # The attributes must match the ones it was set with or the browser keeps
    # the original cookie and the user stays signed in.
    response.delete_cookie(
        key=settings.AUTH_COOKIE_NAME,
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
        path="/",
    )


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> object:
    """
    Who the cookie belongs to. The frontend's source of truth for auth state,
    since it cannot read the httpOnly cookie itself.
    """
    return user
