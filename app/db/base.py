from datetime import datetime

from sqlalchemy import MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Postgres auto-names constraints when you don't, and those generated names
# differ between environments — which makes an Alembic downgrade unable to find
# the index it is meant to drop. Naming them deterministically here means every
# migration refers to the same identifiers everywhere.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative base. Every model inherits from this."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class TimestampMixin:
    """
    Adds `created_at` / `updated_at`.

    Both defaults are `server_default` rather than Python-side, so rows written
    by a migration, a psql session or another service still get correct
    timestamps — the database is the only writer that sees every insert.
    """

    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
