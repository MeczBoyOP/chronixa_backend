from enum import StrEnum

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Role(StrEnum):
    """
    Who can do what. Two values today; the panel is built to grow into more.
    """

    SUPERADMIN = "superadmin"
    ADMIN = "admin"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Stored lowercase — see `repositories.user`. Postgres compares strings
    # case-sensitively, so without normalising, Dib@x.com and dib@x.com are two
    # accounts that both look correct to whoever typed them.
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(120))

    # ponytail: role is a plain string, not a Postgres ENUM and not a roles
    # table. An ENUM needs ALTER TYPE to add a value; a table costs a join on
    # every authenticated request. Promote to a FK when permissions stop being
    # "which of these labels is it" and start being per-resource grants.
    role: Mapped[str] = mapped_column(String(32), default=Role.ADMIN.value)

    # Deactivate rather than delete: a removed user takes their audit trail and
    # every row that referenced them with it.
    is_active: Mapped[bool] = mapped_column(default=True)

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role})>"
