
"""
scratch/reset_db_and_add_admin.py
─────────────────────────────────
Script to wipe the database and create a default system_admin user.
Usage: python scratch/reset_db_and_add_admin.py
"""

import sys
import os

# Add the project root to sys.path so we can import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.database import engine, init_db, get_db
from db.models import Base, UserRole
from repositories.user_repo import create_user
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reset_database():
    logger.info("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    
    logger.info("Initializing database (creating tables)...")
    init_db()

def create_admin():
    logger.info("Creating system_admin user...")
    try:
        with get_db() as db:
            user = create_user(
                db=db,
                username="admin",
                email="admin@example.com",
                password="admin",
                role=UserRole.system_admin
            )
            logger.info(f"Successfully created user: {user.username} ({user.user_role})")
    except Exception as e:
        logger.error(f"Failed to create admin user: {e}")

if __name__ == "__main__":
    reset_database()
    create_admin()
    logger.info("Database reset and admin creation complete.")
