from app.core.database import SessionLocal
from app.models.user import User
from app.models.worker_type import WorkerType
from app.models.worker import Shipment, ShipmentStatus, Worker
from app.models.inventory import Product, ProductComposition
from collections import defaultdict

def debug_dashboard():
    db = SessionLocal()
    try:
        print("=== DEBUG DASHBOARD STATE ===")
        
        # 1. List All Active Shipments
        shipments = db.query(Shipment).filter(
            Shipment.status.in_([ShipmentStatus.PENDING, ShipmentStatus.PARTIAL])
        ).all()
        
        print(f"\nTotal Active Shipments: {len(shipments)}")
        
        worker_materials = defaultdict(lambda: defaultdict(float))
        for s in shipments:
            balance = s.quantity - (s.returned_quantity or 0)
            print(f"  - Shipment ID {s.id}: Worker {s.worker.name} has {balance} of {s.product.name} (ID {s.product_id})")
            if balance > 0:
                worker_materials[s.worker_id][s.product_id] += balance

        # 2. List All Compositions
        compositions = db.query(ProductComposition).all()
        print(f"\nTotal Compositions Rules: {len(compositions)}")
        recipes = defaultdict(dict)
        for comp in compositions:
            print(f"  - Recipe for {comp.composite_product.name} (ID {comp.composite_id}): Needs {comp.quantity} of {comp.component.name} (ID {comp.component_id})")
            recipes[comp.composite_id][comp.component_id] = comp.quantity

        # 3. Simulate Calculation
        print("\n=== SIMULATION ===")
        total_pending = 0
        
        for w_id, materials in worker_materials.items():
            print(f"\nEvaluating Worker ID {w_id} (Materials: {dict(materials)})")
            
            for prod_id, recipe in recipes.items():
                print(f"  Checking Recipe for Product ID {prod_id}...")
                max_units = float('inf')
                has_components = False
                missing_components = []
                
                for comp_id, req_qty in recipe.items():
                    available = materials.get(comp_id, 0)
                    if available > 0:
                        has_components = True
                    
                    if req_qty > 0:
                        possible = available / req_qty
                        print(f"    - Component ID {comp_id}: Uses {req_qty}, Has {available}. Possible: {possible}")
                        max_units = min(max_units, possible)
                    
                    if available < req_qty:
                         missing_components.append(comp_id)

                if has_components:
                    if max_units == float('inf'):
                        max_units = 0
                    print(f"  -> Result: Can make {int(max_units)} units.")
                    if max_units == 0:
                        print(f"     (Zero because limiting component reached 0. Check missing/low stock components)")
                    total_pending += int(max_units)
                else:
                    print(f"  -> Skipping (Worker has NONE of the components for this recipe)")

        print(f"\nFinal Calculated 'Pending Receive': {total_pending}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    debug_dashboard()
