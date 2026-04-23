"""
seed_admin.py
─────────────
One-time script to initialize the PostgreSQL schema and create the default Admin user.
Run with: python seed_admin.py
"""

from db.database import init_db, get_db
from db.models import UserRole
from repositories.user_repo import create_user, get_user_by_email, log_audit

def main():
    try:
        print("Initializing database schema...")
        init_db()
        print("Schema created.")

        with get_db() as db:
            existing = get_user_by_email(db, "admin@platform.com")
            if not existing:
                admin = create_user(
                    db,
                    username="admin",
                    email="admin@platform.com",
                    password="admin123",
                    role=UserRole.general_admin,
                )
                log_audit(db, "INSERT", user_id=admin.id, target_user_id=admin.id, table_name="users")
                print(f"Default Admin created - email: admin@platform.com / password: admin123")
                print("IMPORTANT: Change this password after first login!")
            else:
                print(f"Admin already exists: {existing.email}")
    except Exception as e:
        print(f"\n[ERROR] Database initialization failed: {repr(e)}\n\nMake sure the database 'course_platform' exists in pgAdmin 4!")

if __name__ == "__main__":
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    main()
