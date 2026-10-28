import os
import sys
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from backend.models_db.base import SessionLocal
from backend.models_db.user import User, Role
from backend.security.auth import get_password_hash

DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "transit-demo")


def seed_users():
    db = SessionLocal()
    try:
        db.query(User).delete()
        for email, role in [("manager@transit.com", Role.manager), ("researcher@transit.com", Role.researcher),
                            ("admin@transit.com", Role.admin)]:
            db.add(User(id=str(uuid.uuid4()), email=email, hashed_password=get_password_hash(DEMO_PASSWORD), role=role))
        db.commit()
        print(f"Users seeded (password: {DEMO_PASSWORD}).")
    except Exception as e:
        db.rollback()
        print(f"Error seeding DB: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_users()
