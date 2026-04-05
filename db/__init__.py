# db/__init__.py
# Exposes the public API of the db package for raw SQL access.
from db.database import get_connection, init_db

__all__ = [
    "get_connection",
    "init_db",
]
