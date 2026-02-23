from sqlalchemy import text
from sqlalchemy.orm import Session
from app.models.company import Company
from app.models.user import User
from app.models.inventory import Category, Product, Movement, AuditLog, ProductComposition
from app.models.worker import Worker, Shipment
from app.models.worker_type import WorkerType

def init_multitenancy(db: Session):
    # 0. Ensure columns exist (Manual migration for existing tables)
    # create_all handles new tables (Company), but not new columns in old tables
    tables_to_check = [
        "users", "categories", "products", "movements", 
        "audit_logs", "workers", "worker_types", "shipments", "product_compositions"
    ]
    
    for table in tables_to_check:
        try:
            # Check if company_id already exists (cross-db way)
            # This is a bit tricky across PG and SQLite, but we'll use a simple approach:
            db.execute(text(f"SELECT company_id FROM {table} LIMIT 1"))
        except Exception:
            # If it fails, the column likely doesn't exist
            db.rollback() # Important to clear the failed state
            try:
                db.execute(text(f"ALTER TABLE {table} ADD COLUMN company_id INTEGER REFERENCES companies(id)"))
                db.commit()
                print(f"Migration: Added company_id to {table}")
            except Exception as e:
                db.rollback()
                print(f"Migration Error on {table}: {e}")

    # 0.1 Handle Financial columns in Products
    try:
        db.execute(text("SELECT unit_cost FROM products LIMIT 1"))
    except Exception:
        db.rollback()
        db.execute(text("ALTER TABLE products ADD COLUMN unit_cost FLOAT DEFAULT 0.0"))
        db.commit()
        print("Migration: Added unit_cost to products")
    
    try:
        db.execute(text("SELECT markup_percentage FROM products LIMIT 1"))
    except Exception:
        db.rollback()
        db.execute(text("ALTER TABLE products ADD COLUMN markup_percentage FLOAT DEFAULT 0.0"))
        db.commit()
        print("Migration: Added markup_percentage to products")

    # 0.2 Handle Logo column in Companies
    try:
        db.execute(text("SELECT logo_data FROM companies LIMIT 1"))
    except Exception:
        db.rollback()
        db.execute(text("ALTER TABLE companies ADD COLUMN logo_data TEXT"))
        db.commit()
        print("Migration: Added logo_data to companies")

    # 1. Ensure "Demonstração" company exists
    demo_company = db.query(Company).filter(Company.name == "Demonstração").first()
    if not demo_company:
        demo_company = Company(name="Demonstração")
        db.add(demo_company)
        db.commit()
        db.refresh(demo_company)
    
    company_id = demo_company.id
    
    # 2. Assign current data to "Demonstração" company if not already assigned
    # Note: We use filter(Model.company_id == None) to find data that needs migration
    
    db.query(User).filter(User.company_id == None).update({"company_id": company_id})
    db.query(Category).filter(Category.company_id == None).update({"company_id": company_id})
    db.query(Product).filter(Product.company_id == None).update({"company_id": company_id})
    db.query(Movement).filter(Movement.company_id == None).update({"company_id": company_id})
    db.query(AuditLog).filter(AuditLog.company_id == None).update({"company_id": company_id})
    db.query(Worker).filter(Worker.company_id == None).update({"company_id": company_id})
    db.query(WorkerType).filter(WorkerType.company_id == None).update({"company_id": company_id})
    db.query(Shipment).filter(Shipment.company_id == None).update({"company_id": company_id})
    db.query(ProductComposition).filter(ProductComposition.company_id == None).update({"company_id": company_id})
    
    db.commit()
