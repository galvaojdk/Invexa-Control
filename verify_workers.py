# verify_workers.py
import sys
import os

# Add the project root to the python path
sys.path.append(os.getcwd())

from app.core.database import SessionLocal, engine, Base
from app.models.worker import Worker, Shipment
from app.models.inventory import Product
from app.models.user import User

def verify():
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created (if not existed).")

    db = SessionLocal()
    try:
        # Check if we can create a worker
        print("Creating test worker...")
        worker = Worker(name="Test Worker", role="Tester", daily_rate=100.0)
        db.add(worker)
        db.commit()
        db.refresh(worker)
        print(f"Worker created with ID: {worker.id}")

        # Check if we can read it back
        saved_worker = db.query(Worker).filter(Worker.id == worker.id).first()
        if saved_worker and saved_worker.name == "Test Worker":
            print("Worker verification SUCCESS.")
        else:
            print("Worker verification FAILED.")

        # Clean up
        db.delete(worker)
        db.commit()
        print("Test worker cleaned up.")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    verify()
