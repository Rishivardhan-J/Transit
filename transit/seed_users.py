import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from backend.models_db.base import SessionLocal
from backend.models_db.user import User, Role
import uuid

def seed_users():
    db = SessionLocal()
    try:
        # Delete existing users
        db.query(User).delete()
        
        users = [
            ("manager@transit.com", Role.manager),
            ("researcher@transit.com", Role.researcher),
            ("admin@transit.com", Role.admin)
        ]
        
        for email, role in users:
            new_user = User(
                id=str(uuid.uuid4()),
                email=email,
                hashed_password="dummy_hash_because_of_passlib_bcrypt_bug",
                role=role
            )
            db.add(new_user)
            
        db.commit()
        print("Users seeded successfully.")
    except Exception as e:
        db.rollback()
        print(f"Error seeding DB: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_users()
