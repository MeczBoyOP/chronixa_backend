from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration, read from environment variables and `.env`.

    Everything the app needs to run lives here — nothing reads os.environ
    directly, so there is exactly one place to look when a deployment behaves
    differently from local.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- application ------------------------------------------------------
    PROJECT_NAME: str = "Chronixa API"
    VERSION: str = "0.1.0"
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # --- security ---------------------------------------------------------
    # Override in every deployed environment. Kept here so that whatever adds
    # auth later has a key to sign with.
    # Long enough to satisfy HS256's 32-byte minimum so local runs are quiet,
    # and recognisable enough that the validator below can refuse it anywhere
    # that isn't local.
    SECRET_KEY: str = "local-development-only-change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # The session cookie. httpOnly, so the token is unreadable from JavaScript:
    # an XSS bug can then act as the user for as long as the page is open, but
    # cannot walk off with a credential that keeps working for a day after.
    AUTH_COOKIE_NAME: str = "chronixa_session"

    # --- bootstrap accounts -----------------------------------------------
    # Read by `python -m app.scripts.seed`. Empty by default and kept out of
    # the code so real credentials never reach git.
    SEED_SUPERADMIN_EMAIL: str = ""
    SEED_SUPERADMIN_NAME: str = "Super Admin"
    SEED_SUPERADMIN_PASSWORD: str = ""
    SEED_ADMIN_EMAIL: str = ""
    SEED_ADMIN_NAME: str = "Admin"
    SEED_ADMIN_PASSWORD: str = ""

    # --- CORS -------------------------------------------------------------
    # The Next.js dev server. In practice the frontend proxies /api through
    # its own origin (see frontend/next.config rewrites), so this only matters
    # for direct calls made outside that proxy.
    CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"]
    )

    # --- database ---------------------------------------------------------
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "chronixa"

    # Connection pool. Defaults suit a single app instance in development;
    # size these against your Postgres `max_connections` before deploying.
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_PRE_PING: bool = True
    DB_ECHO: bool = False

    @model_validator(mode="after")
    def _reject_weak_secret_outside_local(self) -> "Settings":
        """
        Fail to boot rather than sign tokens with a guessable key.

        A short or default SECRET_KEY is not a warning — anyone holding it can
        mint a valid superadmin session. Caught here, at startup, because the
        alternative is finding out from the access logs.
        """
        if self.ENVIRONMENT == "local":
            return self

        if self.SECRET_KEY.startswith("local-development-only"):
            raise ValueError(
                f"SECRET_KEY is still the development default in "
                f"ENVIRONMENT={self.ENVIRONMENT}. Generate one with: "
                'python -c "import secrets; print(secrets.token_urlsafe(32))"'
            )

        if len(self.SECRET_KEY.encode()) < 32:
            raise ValueError(
                "SECRET_KEY must be at least 32 bytes (RFC 7518 §3.2 for HS256); "
                f"got {len(self.SECRET_KEY.encode())}."
            )

        return self

    @computed_field
    @property
    def COOKIE_SECURE(self) -> bool:
        """
        HTTPS-only everywhere but local.

        A `Secure` cookie is silently dropped over plain http, so hardcoding it
        True makes local login fail with no error anywhere — the browser just
        never stores the cookie.
        """
        return self.ENVIRONMENT != "local"

    @computed_field
    @property
    def DATABASE_URL(self) -> PostgresDsn:
        """
        Async DSN for the application (asyncpg driver).

        Assembled from the parts rather than accepted as one string so that a
        password containing `@` or `/` can't silently corrupt the URL — Pydantic
        quotes each component for us.
        """
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )

    @computed_field
    @property
    def SYNC_DATABASE_URL(self) -> PostgresDsn:
        """
        Same database over a blocking driver.

        Some tooling can't drive an async engine — this is the escape hatch for
        it. Alembic uses the async URL above and does not need this.
        """
        return PostgresDsn.build(
            scheme="postgresql+psycopg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )


@lru_cache
def get_settings() -> Settings:
    """
    Cached accessor.

    Settings are read once per process: constructing them re-reads and re-parses
    the `.env` file, which is wasteful inside a request and makes configuration
    look mutable when it isn't.
    """
    return Settings()


settings = get_settings()
