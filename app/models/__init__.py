"""
SQLAlchemy models.

Every model must be imported here. Alembic's autogenerate compares the database
against `Base.metadata`, and a model class only registers itself on that
metadata when its module is imported — a model missing from this file is
silently absent from every migration it should have appeared in.

`__all__` is the list Alembic's env.py relies on being complete.
"""

from app.models.user import Role, User

__all__: list[str] = ["Role", "User"]
