from collections.abc import Callable, Coroutine
from typing import Annotated, Any

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import decode_access_token
from app.db.session import get_session
from app.models.user import Role, User
from app.repositories import user as user_repo

# Shared dependencies live here so routers import one name instead of reaching
# into the db package themselves.
SessionDep = Annotated[AsyncSession, Depends(get_session)]

# 401 for "we don't know who you are", 403 for "we do, and you may not".
# Collapsing them tells an attacker nothing, but it also tells the FRONTEND
# nothing — and it needs the difference to choose between redirecting to login
# and showing "not permitted".
_UNAUTHENTICATED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
)


async def get_current_user(
    db: SessionDep,
    token: Annotated[str | None, Cookie(alias=settings.AUTH_COOKIE_NAME)] = None,
) -> User:
    """
    The signed-in user, from the session cookie.

    The token is re-checked against the database on every request rather than
    trusted on its claims alone. A JWT stays valid until it expires, so without
    this lookup a deactivated account keeps full access for up to a day.
    """
    if not token:
        raise _UNAUTHENTICATED

    claims = decode_access_token(token)
    if claims is None:
        raise _UNAUTHENTICATED

    try:
        user_id = int(claims["sub"])
    except (KeyError, TypeError, ValueError):
        raise _UNAUTHENTICATED from None

    user = await user_repo.get_by_id(db, user_id)
    if user is None or not user.is_active:
        raise _UNAUTHENTICATED

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(
    *roles: Role,
) -> Callable[[User], Coroutine[Any, Any, User]]:
    """
    Route guard: `_: Annotated[User, Depends(require_roles(Role.SUPERADMIN))]`.

    Takes roles varargs rather than a single one so a route can accept several
    without the caller building a set at every call site.
    """
    allowed = {role.value for role in roles}

    async def guard(user: CurrentUser) -> User:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
            )
        return user

    return guard


# The common case, named once so routes don't repeat the wiring.
SuperAdminDep = Annotated[User, Depends(require_roles(Role.SUPERADMIN))]
