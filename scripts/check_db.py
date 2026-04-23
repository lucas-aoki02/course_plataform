from sqlalchemy import text
from db.database import engine

def check():
    with engine.connect() as conn:
        res = conn.execute(text("SELECT enumlabel FROM pg_enum JOIN pg_type ON pg_enum.enumtypid = pg_type.oid WHERE pg_type.typname = 'userrole';"))
        labels = [r[0] for r in res]
        print(f"Current enum labels: {labels}")
        
        res = conn.execute(text("SELECT DISTINCT role FROM users;"))
        roles = [r[0] for r in res]
        print(f"Roles in users table: {roles}")

if __name__ == "__main__":
    check()
