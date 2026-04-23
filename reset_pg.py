from db.database import engine
from db.models import Base
import logging

def reset_db():
    print("Dropping all PostgreSQL tables...")
    # Base.metadata.drop_all() might fail if there are tables not in metadata or complicated dependencies,
    # but it usually works for SQLAlchemy models.
    Base.metadata.drop_all(bind=engine)
    print("Creating all PostgreSQL tables with new schema...")
    Base.metadata.create_all(bind=engine)
    print("Done.")

if __name__ == "__main__":
    reset_db()
