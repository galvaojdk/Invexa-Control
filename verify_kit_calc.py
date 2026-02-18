from app.core.database import SessionLocal
from app.models.user import User
from app.models.worker_type import WorkerType
from app.models.worker import Shipment, ShipmentStatus, Worker
from app.models.inventory import Product, ProductComposition
from sqlalchemy import func
from collections import defaultdict

def simulate_dashboard_calc():
    db = SessionLocal()
    try:
        print("Simulando calculo atual...")
        
        # 1. Setup Mock Data (if not exists from previous steps)
        # We assume the user followed the prompt and the previous 'seed_products.py' ran.
        # We need to simulate the Shipments mentioned: 10m Fabric, 20 Sleeves, 40 Buttons.
        
        # Find the products
        tecido = db.query(Product).filter(Product.name == "Tecido Branco").first()
        manga = db.query(Product).filter(Product.name == "Manga de Camisa").first()
        botoes = db.query(Product).filter(Product.name == "Botão").first() # Attention to accent
        camisa = db.query(Product).filter(Product.name == "Camisa Branca").first()
        
        if not all([tecido, manga, botoes, camisa]):
            print("Erro: Produtos nao encontrados. Rode o seed_products.py primeiro.")
            return

        # Create a Dummy Worker
        worker = db.query(Worker).filter(Worker.name == "Costureira Teste").first()
        if not worker:
            worker = Worker(name="Costureira Teste", active=True, role="costureira")
            db.add(worker)
            db.commit()
            
        # Create Shipments (Clean old ones for this worker first to be sure)
        db.query(Shipment).filter(Shipment.worker_id == worker.id).delete()
        db.commit()
        
        s1 = Shipment(worker_id=worker.id, product_id=tecido.id, quantity=10, cost_per_unit=0, status=ShipmentStatus.PENDING)
        s2 = Shipment(worker_id=worker.id, product_id=manga.id, quantity=20, cost_per_unit=0, status=ShipmentStatus.PENDING)
        s3 = Shipment(worker_id=worker.id, product_id=botoes.id, quantity=40, cost_per_unit=0, status=ShipmentStatus.PENDING)
        
        db.add_all([s1, s2, s3])
        db.commit()
        
        # 2. CURRENT WRONG CALCULATION
        current_calc = db.query(
            func.sum(Shipment.quantity - func.coalesce(Shipment.returned_quantity, 0))
        ).filter(
            Shipment.status.in_([ShipmentStatus.PENDING, ShipmentStatus.PARTIAL])
        ).scalar() or 0
        
        print(f"Calculo Atual (Soma Simples): {current_calc}") # Should be 70
        
        # 3. PROPOSED LOGIC (Reverse Composition)
        print("\nCalculando pela Logica de Kits...")
        
        # Fetch all active shipments
        active_shipments = db.query(Shipment).filter(
            Shipment.status.in_([ShipmentStatus.PENDING, ShipmentStatus.PARTIAL])
        ).all()
        
        # Group materials by Worker
        worker_materials = defaultdict(lambda: defaultdict(float))
        for s in active_shipments:
            balance = s.quantity - (s.returned_quantity or 0)
            if balance > 0:
                worker_materials[s.worker_id][s.product_id] += balance
                
        # Fetch Compositions
        compositions = db.query(ProductComposition).all()
        
        # Map CompositeID -> { ComponentID: Qty }
        recipes = defaultdict(dict)
        for comp in compositions:
            recipes[comp.composite_id][comp.component_id] = comp.quantity
            
        total_pending_products = 0
        
        for w_id, materials in worker_materials.items():
            print(f"\nWorker {w_id} materials: {dict(materials)}")
            
            # Simple Greedy matching? 
            # Or assume 1 worker = 1 product type primarily?
            # Let's try to find the match that consumes most materials or just the first valid one.
            
            # For this scenario, we only have one recipe: Camisa Branca.
            
            possible_products = 0
            
            # Check each recipe
            for prod_id, recipe in recipes.items():
                # Check limiting factor
                max_units = float('inf')
                has_at_least_one_component = False
                
                for comp_id, req_qty in recipe.items():
                    available = materials.get(comp_id, 0)
                    if available > 0:
                        has_at_least_one_component = True
                    
                    if req_qty > 0:
                        max_units = min(max_units, available / req_qty)
                    else:
                        max_units = 0
                
                if has_at_least_one_component and max_units != float('inf'):
                    print(f"  Pode fazer {max_units} do produto ID {prod_id}")
                    # If we assume this is the product being made:
                    possible_products += int(max_units)
                    
                    # Deduct materials? 
                    # If we have shared components, we must deduct.
                    # But for now let's just assume distinct production lines or non-overlapping recipes for simplicity 
                    # unless complex.
            
            total_pending_products += possible_products

        print(f"\nResultado Novo (Previsao): {total_pending_products}")

    except Exception as e:
        print(f"Erro: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    simulate_dashboard_calc()
