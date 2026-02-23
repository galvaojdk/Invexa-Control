from datetime import datetime, timedelta
from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.models.inventory import Product, Movement, MovementType
from app.models.user import User
from app.api.dependencies import get_db, login_required

router = APIRouter(prefix="/reports", tags=["Reports"])
templates = Jinja2Templates(directory="app/templates")

from app.models.worker import Shipment, Worker, ShipmentStatus

@router.get("")
@router.get("/")
async def reports_view(
    request: Request,
    report_type: str = "stock",
    start_date: str = None,
    end_date: str = None,
    product_id: str = None,
    category_id: str = None,
    worker_id: str = None,
    user: User = Depends(login_required),
    db: Session = Depends(get_db)
):
    # Sanitize Inputs (Handle empty strings from HTML forms)
    if product_id == "": product_id = None
    if category_id == "": category_id = None
    if worker_id == "": worker_id = None
    
    if product_id: product_id = int(product_id)
    if category_id: category_id = int(category_id)
    if worker_id: worker_id = int(worker_id)

    # Fetch common data for filters
    all_products = db.query(Product).filter(Product.company_id == user.company_id).order_by(Product.name).all()
    # Need to import Category if not imported, or query it dynamically if model is available
    from app.models.inventory import Category # local import to ensure availability or assume global import
    all_categories = db.query(Category).filter(Category.company_id == user.company_id).order_by(Category.name).all()
    all_workers = db.query(Worker).filter(Worker.company_id == user.company_id).order_by(Worker.name).all()

    # Common context
    context = {
        "request": request,
        "user": user,
        "report_type": report_type,
        "all_products": all_products,
        "all_categories": all_categories,
        "all_workers": all_workers,
        "product_id": product_id,
        "category_id": category_id,
        "worker_id": worker_id
    }

    # Helper: Date Filters parsing
    filter_start = None
    filter_end = None
    if start_date:
        filter_start = datetime.strptime(start_date, "%Y-%m-%d")
    if end_date:
        filter_end = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1) # End of day

    if report_type == "outsourced":
        # Fetch data for Outsourced Shipments Report
        query = db.query(Shipment).join(Worker).join(Product).filter(Shipment.company_id == user.company_id).order_by(Shipment.created_at.desc())
        
        if filter_start:
            query = query.filter(Shipment.created_at >= filter_start)
        if filter_end:
            query = query.filter(Shipment.created_at <= filter_end)
        if product_id:
            query = query.filter(Shipment.product_id == product_id)
        if worker_id:
            query = query.filter(Shipment.worker_id == worker_id)
        if category_id:
            query = query.filter(Product.category_id == category_id)
            
        shipments = query.all()
        
        # Calculate balance for each shipment
        report_data = []
        for s in shipments:
            report_data.append({
                "date": s.created_at,
                "worker": s.worker.name,
                "product": s.product.name,
                "quantity": s.quantity,
                "returned": s.returned_quantity,
                "balance": s.quantity - s.returned_quantity,
                "status": s.status.value
            })
        context["report_data"] = report_data
        
        context["report_data"] = report_data

    elif report_type == "worker_review":
        # 1. Fetch Materials in Power (Pending Shipments)
        shipments_query = db.query(Shipment).join(Worker).join(Product)\
            .filter(Shipment.status != ShipmentStatus.CANCELLED)\
            .filter(Shipment.quantity > Shipment.returned_quantity)\
            .filter(Shipment.company_id == user.company_id)\
            .order_by(Worker.name, Product.name)
            
        if filter_start:
             shipments_query = shipments_query.filter(Shipment.created_at >= filter_start)
        if filter_end:
             shipments_query = shipments_query.filter(Shipment.created_at <= filter_end)
        if worker_id:
             shipments_query = shipments_query.filter(Shipment.worker_id == worker_id)
        if product_id:
             shipments_query = shipments_query.filter(Shipment.product_id == product_id)
        
        pending_shipments = shipments_query.all()
        
        # 2. Fetch Production History (Delivered Finished Goods)
        movements_query = db.query(Movement).join(Product)\
            .filter(Movement.type == MovementType.IN)\
            .filter(Movement.reason.like("Produção Recebida de%"))\
            .filter(Movement.company_id == user.company_id)\
            .order_by(Movement.timestamp.desc())

        if filter_start:
             movements_query = movements_query.filter(Movement.timestamp >= filter_start)
        if filter_end:
             movements_query = movements_query.filter(Movement.timestamp <= filter_end)
        
        if worker_id:
            target_worker = db.query(Worker).filter(Worker.id == worker_id, Worker.company_id == user.company_id).first()
            if target_worker:
                 movements_query = movements_query.filter(Movement.reason == f"Produção Recebida de {target_worker.name}")
        
        if product_id:
             movements_query = movements_query.filter(Movement.product_id == product_id)
             
        production_movements = movements_query.all()

        # Fetch Product Compositions for potential production calculation
        from app.models.inventory import ProductComposition
        all_compositions = db.query(ProductComposition).join(Product, ProductComposition.composite_id == Product.id).filter(
            Product.company_id == user.company_id
        ).all()
        compositions_map = {}
        for c in all_compositions:
            if c.composite_id not in compositions_map:
                compositions_map[c.composite_id] = []
            compositions_map[c.composite_id].append({
                "component_id": c.component_id,
                "quantity": c.quantity
            })
        
        # 3. Aggregate Data by Worker
        final_data = {}
        
        # Process Pending (Shipments have Worker relation, so we know name)
        for s in pending_shipments:
            w_name = s.worker.name
            if w_name not in final_data:
                final_data[w_name] = {"name": w_name, "materials": [], "delivered": []}
            
            balance = s.quantity - s.returned_quantity
            existing = next((i for i in final_data[w_name]["materials"] if i["product_id"] == s.product_id), None)
            
            if existing:
                existing["sent"] += s.quantity
                existing["returned"] += s.returned_quantity
                existing["balance"] += balance
                # Update last sent date if this shipment is newer
                if s.created_at > existing["last_sent_date"]:
                    existing["last_sent_date"] = s.created_at
            else:
                final_data[w_name]["materials"].append({
                    "product_id": s.product_id,
                    "product": s.product.name,
                    "unit": s.product.unit,
                    "sent": s.quantity,
                    "returned": s.returned_quantity,
                    "balance": balance,
                    "last_sent_date": s.created_at
                })
                
        # Process Production Movements
        for m in production_movements:
            if "Produção Recebida de " not in m.reason:
                continue
                
            w_name = m.reason.replace("Produção Recebida de ", "").strip()
            
            # Filter if worker_id was passed (safety check if names match)
            if worker_id:
                target_worker = db.query(Worker).filter(Worker.id == worker_id, Worker.company_id == user.company_id).first()
                if target_worker and target_worker.name != w_name:
                    continue

            if w_name not in final_data:
                 final_data[w_name] = {"name": w_name, "materials": [], "delivered": []}
            
            # Aggregate Delivered Items (Finished Goods)
            existing = next((i for i in final_data[w_name]["delivered"] if i["product_id"] == m.product_id), None)
             
            if existing:
                existing["quantity"] += m.quantity
                if m.timestamp > existing["last_date"]:
                    existing["last_date"] = m.timestamp
            else:
                final_data[w_name]["delivered"].append({
                    "product_id": m.product_id,
                    "product": m.product.name,
                    "unit": m.product.unit,
                    "quantity": m.quantity,
                    "last_date": m.timestamp,
                    "potential": 0 # Placeholder
                })

        # Calculate Potential Production
        for w_data in final_data.values():
            materials_map = {m["product_id"]: m["balance"] for m in w_data["materials"]}
            
            for item in w_data["delivered"]:
                pid = item["product_id"]
                if pid in compositions_map:
                    possible_counts = []
                    for comp in compositions_map[pid]:
                        cid = comp["component_id"]
                        req_qty = comp["quantity"]
                        
                        if req_qty > 0 and cid in materials_map and materials_map[cid] > 0:
                            count = int(materials_map[cid] / req_qty)
                            possible_counts.append(count)
                        else:
                            possible_counts.append(0)
                    
                    # The limiting factor determines the potential
                    item["potential"] = min(possible_counts) if possible_counts else 0
                else:
                    item["potential"] = 0

        report_data = list(final_data.values())
        # Sort by Name
        report_data.sort(key=lambda x: x["name"])
        
        context["report_data"] = report_data
        
    elif report_type == "worker_deliveries":
        # Report for Delivered Finished Goods (Production Received) from Workers
        
        # We query Movements of type IN where the reason indicates "Produção Recebida de {WorkerName}"
        query = db.query(Movement).join(Product).filter(
            Movement.type == MovementType.IN,
            Movement.reason.like("Produção Recebida de%"),
            Movement.company_id == user.company_id
        ).order_by(Movement.timestamp.desc())

        if filter_start:
            query = query.filter(Movement.timestamp >= filter_start)
        if filter_end:
            query = query.filter(Movement.timestamp <= filter_end)
        if product_id:
            query = query.filter(Movement.product_id == product_id)
        
        # If worker_id is provided, we need to filter by name because the Movement record 
        # stores the worker name in the 'reason' string, not the ID directly in a relationship 
        # (though ideally it should have a sector link or separate table).
        if worker_id:
            target_worker = db.query(Worker).filter(Worker.id == worker_id, Worker.company_id == user.company_id).first()
            if target_worker:
                 query = query.filter(Movement.reason == f"Produção Recebida de {target_worker.name}")
            else:
                 # Worker ID provided but not found? Return empty result or handle error.
                 # For safety, filter by impossible condition
                 query = query.filter(Movement.id == -1)

        movements = query.all()

        report_data = []
        for m in movements:
            # Extract Worker Name from Reason
            # Format: "Produção Recebida de {Name}"
            worker_name = m.reason.replace("Produção Recebida de ", "").strip()
            
            report_data.append({
                "date": m.timestamp,
                "worker": worker_name,
                "product": m.product.name,
                "unit": m.product.unit,
                "quantity": m.quantity
            })
            
        context["report_data"] = report_data

    elif report_type == "movements_history":
        # Global Movements History Report
        query = db.query(Movement).join(Product).filter(Movement.company_id == user.company_id).order_by(Movement.timestamp.desc())

        if filter_start:
            query = query.filter(Movement.timestamp >= filter_start)
        if filter_end:
            query = query.filter(Movement.timestamp <= filter_end)
        if product_id:
            query = query.filter(Movement.product_id == product_id)
        if category_id:
            query = query.filter(Product.category_id == category_id)
            
        # Limit only if no filter (or very loose filter) to prevent massive scan
        if not filter_start and not product_id and not category_id:
            query = query.limit(500)
            
        movements = query.all()

        report_data = []
        for m in movements:
            report_data.append({
                "date": m.timestamp,
                "product": m.product.name,
                "type": m.type.value,
                "quantity": m.quantity,
                "reason": m.reason or "-",
                "sector": m.sector or "-",
                "user": m.user.full_name if m.user else "-"
            })
        context["report_data"] = report_data

    else: # Default: 'stock'
        # Stock Position Report
        query = db.query(Product).filter(Product.company_id == user.company_id)
        
        if category_id:
            query = query.filter(Product.category_id == category_id)
        if product_id:
            query = query.filter(Product.id == product_id)
            
        products = query.order_by(Product.name.asc()).all()
        context["products"] = products
        context["gen_date"] = datetime.now()

    return templates.TemplateResponse("reports.html", context)
