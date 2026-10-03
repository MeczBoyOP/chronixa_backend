from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

engine: AsyncEngine = create_async_engine(
    str(settings.DATABASE_URL),
    echo=settings.DB_ECHO,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    # Checks a pooled connection is still alive before handing it out. Costs one
    # round trip; saves the stale-connection errors you otherwise get after a
    # database restart or an idle-timeout on a managed Postgres.
    pool_pre_ping=settings.DB_POOL_PRE_PING,
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    # Objects stay usable after commit(). With the default True, every attribute
    # access post-commit fires a fresh SELECT — and in an async session that
    # lazy load raises rather than silently querying.
    expire_on_commit=False,
    autoflush=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency yielding a session scoped to one request.

    The session is closed on the way out whatever happens. Committing is left to
    the caller: a dependency that auto-commits will happily persist half of a
    failed operation.
    """
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def dispose_engine() -> None:
    """Close every pooled connection. Called on application shutdown."""
    await engine.dispose()
