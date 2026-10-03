# Chronixa — Backend

FastAPI service backed by PostgreSQL. This is the project skeleton: wiring,
configuration and migrations are in place; there are no endpoints yet.

## Stack

| Concern       | Choice                                  |
| ------------- | --------------------------------------- |
| Framework     | FastAPI 0.141                           |
| Server        | Uvicorn (via `fastapi[standard]`)       |
| ORM           | SQLAlchemy 2.0, async                   |
| Driver        | asyncpg                                 |
| Migrations    | Alembic (async template)                |
| Config        | pydantic-settings                       |
| Lint / format | Ruff                                    |
| Tests         | pytest + pytest-asyncio                 |
| Python        | 3.12+ (verified on 3.14)                |

## Getting started

```bash
cd backend

# 1. Virtualenv (already created as .venv — skip if present)
python -m venv .venv
source .venv/Scripts/activate      # Windows bash;  .venv\Scripts\activate on cmd/PowerShell
                                   # macOS/Linux:   source .venv/bin/activate

# 2. Dependencies
pip install -r requirements-dev.txt

# 3. Configuration
cp .env.example .env               # then set POSTGRES_PASSWORD at minimum

# 4. Create the database
createdb chronixa                  # or: psql -U postgres -c "CREATE DATABASE chronixa;"

# 5. Run
fastapi dev app/main.py            # http://127.0.0.1:8000  ·  docs at /docs
```

`fastapi dev` reloads on save. For production use `fastapi run app/main.py` or
point a process manager at `app.main:app`.

## Layout

```text
backend/
├── app/
│   ├── main.py            # app factory, CORS, lifespan, /health
│   ├── core/
│   │   └── config.py      # Settings — the only place env vars are read
│   ├── db/
│   │   ├── base.py        # DeclarativeBase + naming convention + TimestampMixin
│   │   └── session.py     # async engine, sessionmaker, get_session dependency
│   ├── models/            # SQLAlchemy models  (must be imported in __init__.py)
│   ├── schemas/           # Pydantic request/response models
│   ├── repositories/      # database access — queries live here, not in routes
│   ├── services/          # business logic — orchestrates repositories
│   └── api/
│       ├── deps.py        # shared dependencies (SessionDep)
│       └── v1/
│           └── router.py  # v1 router — empty, mounted at /api/v1
├── alembic/               # migration environment
│   ├── env.py             # reads the URL from app.core.config
│   └── versions/          # migration scripts
├── tests/
├── alembic.ini
├── pyproject.toml         # ruff + pytest config
├── requirements.txt
└── .env.example
```

The layering is deliberate: **route → service → repository → model**. Routes
handle HTTP and nothing else; services hold the rules; repositories own the
queries. Keeping SQL out of route handlers is what makes the logic testable
without an HTTP client.

## Adding your first model

```python
# app/models/user.py
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True, index=True)
```

```python
# app/models/__init__.py  — required, see the note in that file
from app.models.user import User  # noqa: F401

__all__ = ["User"]
```

## Migrations

```bash
alembic revision --autogenerate -m "add users table"   # needs a reachable database
alembic upgrade head
alembic downgrade -1
alembic upgrade head --sql                             # print SQL, connect to nothing
```

Autogenerate compares the live database against `Base.metadata`. **Always read
the generated migration before applying it** — it infers intent from a schema
diff and cannot tell a rename from a drop-plus-add.

The database URL is injected into Alembic from `app.core.config`, so migrations
and the application can never drift onto different databases. Don't set
`sqlalchemy.url` in `alembic.ini`.

## Checks

```bash
ruff check .          # lint
ruff check . --fix
ruff format .         # format
pytest                # tests
```

## Notes

- `/health` is a liveness probe, not a feature endpoint. It deliberately does
  not touch the database — a health check that fails on a Postgres blip gets a
  healthy app restarted. Add a separate readiness endpoint if you need to gate
  traffic on database reachability.
- `/docs`, `/redoc` and `/openapi.json` are served only when `DEBUG=true`. Set
  `DEBUG=false` in any deployed environment.
- `SECRET_KEY` must be replaced before deploying:
  `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
- `CORS_ORIGINS` must list the frontend origin exactly — scheme, host and port.
  The Vite dev server default (`http://localhost:5173`) is already there.
