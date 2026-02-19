import sys
import os
sys.path.append(os.getcwd())
from app.core.database import SessionLocal
from app.models.worker import Shipment
from app.models.inventory import Product, Movement

db = SessionLocal()
print("--- DEBUG START ---")
# Check shipments for Jaleco Branco
prods = db.query(Product).filter(Product.name.like("%Jaleco Branco%")).all()
for p in prods:
    print(f"Prod: {p.name} (ID: {p.id}, Comp: {p.is_composite})")
    ships = db.query(Shipment).filter(Shipment.product_id == p.id).all()
    for s in ships:
        print(f"  Shipment {s.id}: Status={s.status}, Return={s.returned_quantity}, Updated={s.updated_at}")
    
    movs = db.query(Movement).filter(Movement.product_id == p.id).order_by(Movement.timestamp.desc()).limit(5).all()
    for m in movs:
        print(f"  Mov {m.id}: {m.timestamp} {m.type} {m.quantity} {m.reason}")
print("--- DEBUG END ---")
