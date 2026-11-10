import sys
import os
from sqlalchemy.orm import Session

# Add the project root to the python path
sys.path.append(os.getcwd())

from app.core.database import SessionLocal
from app.models.user import User
from app.models.company import Company
from app.models.inventory import Category, Product, Movement # Load these
from app.models.worker import Worker, Shipment              # Load these
from app.models.worker_type import WorkerType               # Load these
from app.models.production import ProductionOrder, OPMaterial
from app.models.ticket import SupportTicket, TicketMessage
from app.models.system import SystemGuide
from app.core.security import get_password_hash

def reset_admin(email, password):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        
        # Get demo company
        demo_company = db.query(Company).filter(Company.name == "Demonstração").first()
        if not demo_company:
            print("Error: Demo company not found. Please run the server once first.")
            return

        hashed_password = get_password_hash(password)
        
        if user:
            print(f"Updating existing user: {email}")
            user.hashed_password = hashed_password
            user.is_admin = True
            user.company_id = demo_company.id
        else:
            print(f"Creating new admin user: {email}")
            user = User(
                email=email,
                hashed_password=hashed_password,
                full_name="Administrador",
                is_admin=True,
                company_id=demo_company.id
            )
            db.add(user)
            
        db.commit()
        print(f"Success! User {email} is now an admin with password: {password}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    email = sys.argv[1] if len(sys.argv) > 1 else "admin@invexa.com"
    pwd = sys.argv[2] if len(sys.argv) > 2 else "admin123"
    reset_admin(email, pwd)
