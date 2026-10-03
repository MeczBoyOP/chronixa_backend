from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.db.session import dispose_engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Startup and shutdown.

    Nothing to open on startup — the engine builds its pool lazily on first use.
    On the way out the pool is disposed so the process doesn't leave Postgres
    connections hanging around after a reload or a container stop.
    """
    yield
    await dispose_engine()


def create_app() -> FastAPI:
    """
    Application factory.

    A factory rather than a module-level instance so tests can build an app with
    overridden settings instead of importing whatever the environment happened
    to configure at import time.
    """
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        # Interactive docs are a description of your entire attack surface;
        # they stay off outside development.
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    if settings.CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @app.get("/health", tags=["meta"], include_in_schema=False)
    async def health() -> dict[str, str]:
        """
        Liveness probe — not a feature endpoint.

        Deliberately does not touch the database: a health check that fails when
        Postgres blips will have your orchestrator restart a perfectly healthy
        app. Add a separate readiness endpoint if you need to gate traffic on
        the database being reachable.
        """
        return {"status": "ok", "environment": settings.ENVIRONMENT}

    return app


app = create_app()
