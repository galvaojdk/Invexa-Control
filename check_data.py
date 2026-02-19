
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker
from app.models.inventory import Product, Movement
from app.models.worker import Shipment
from app.core.database import Base
from datetime import datetime, timedelta

engine = create_engine("sqlite:///invexa.db")
Session = sessionmaker(bind=engine)
session = Session()

# 1. Check Product
print("--- Product ---")
prod = session.query(Product).filter(Product.name.like("%Jaleco Branco%")).first()
if prod:
    print(f"ID: {prod.id}, Name: {prod.name}, Is Composite: {prod.is_composite}")
else:
    print("Product not found")
    exit()

# 2. Check Movements
print("\n--- Movements (Last 30 Days) ---")
thirty_days_ago = datetime.now() - timedelta(days=30)
movements = session.query(Movement).filter(
    Movement.product_id == prod.id,
    Movement.timestamp >= thirty_days_ago
).order_by(Movement.timestamp.desc()).all()

for m in movements:
    print(f"ID: {m.id}, Date: {m.timestamp}, Type: {m.type}, Qty: {m.quantity}, Reason: {m.reason}")

# 3. Check Shipments
print("\n--- Shipments (Last 30 Days) ---")
shipments = session.query(Shipment).filter(
    Shipment.product_id == prod.id,
    Shipment.updated_at >= thirty_days_ago
).order_by(Shipment.updated_at.desc()).all()

for s in shipments:
    print(f"ID: {s.id}, Product: {s.product.name}, Return Qty: {s.returned_quantity}, Updated At: {s.updated_at}")
    
session.close()
