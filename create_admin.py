# create_admin.py
import sys
import os
from sqlalchemy.orm import Session

# Add the project root to the python path
sys.path.append(os.getcwd())

from app.core.database import SessionLocal, Base, engine
from app.models.user import User
from app.core.security import get_password_hash

def create_admin(email, password, full_name="Admin"):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            print(f"User {email} already exists.")
            return

        print(f"Creating admin user: {email}")
        hashed_password = get_password_hash(password)
        new_user = User(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            is_active=True,
            is_admin=True,
            is_premium=True,
            subscription_status="active",
            subscription_plan="Premium Admin"
        )
        db.add(new_user)
        db.commit()
        print(f"Admin user {email} created successfully!")
    except Exception as e:
        print(f"Error creating user: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python create_admin.py <email> <password> [full_name]")
        print("Example: python create_admin.py admin@invexa.com admin123")
    else:
        email = sys.argv[1]
        password = sys.argv[2]
        full_name = sys.argv[3] if len(sys.argv) > 3 else "Administrador"
        create_admin(email, password, full_name)
