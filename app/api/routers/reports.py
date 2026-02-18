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
    product_id: int = None,
    category_id: int = None,
    worker_id: int = None,
    user: User = Depends(login_required),
    db: Session = Depends(get_db)
):
    # Fetch common data for filters
    all_products = db.query(Product).order_by(Product.name).all()
    # Need to import Category if not imported, or query it dynamically if model is available
    from app.models.inventory import Category # local import to ensure availability or assume global import
    all_categories = db.query(Category).order_by(Category.name).all()
    all_workers = db.query(Worker).order_by(Worker.name).all()

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
        query = db.query(Shipment).join(Worker).join(Product).order_by(Shipment.created_at.desc())
        
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
        # Assuming Production Entries are movements of Type IN with specific reason or sector
        # Ideally production creates a Movement IN with reason "Produção Recebida de {worker_name}"
        # We can filter by reason string pattern if we don't have a structured link.
        # This is Fragile but fits current implementation of production.py
        
        movements_query = db.query(Movement).join(Product)\
            .filter(Movement.type == MovementType.IN)\
            .filter(Movement.reason.like("Produção Recebida de%"))\
            .order_by(Movement.timestamp.desc())

        if filter_start:
             movements_query = movements_query.filter(Movement.timestamp >= filter_start)
        if filter_end:
             movements_query = movements_query.filter(Movement.timestamp <= filter_end)
        
        # We need to filter by worker name extracted from reason string if filtering by worker_id?
        # That's very hard with just SQL LIKE.
        # Better approach: If worker_id is present, get worker name and filter by exact string.
        # If no worker_id, we fetch all and group in python.
        
        if worker_id:
            target_worker = db.query(Worker).get(worker_id)
            if target_worker:
                 movements_query = movements_query.filter(Movement.reason == f"Produção Recebida de {target_worker.name}")
        
        if product_id:
             movements_query = movements_query.filter(Movement.product_id == product_id)
             
        production_movements = movements_query.all()
        
        # 3. Aggregate Data by Worker
        aggregated = {}

        # Process Pending Materials
        for s in pending_shipments:
            w_id = s.worker_id
            if w_id not in aggregated:
                aggregated[w_id] = {
                    "name": s.worker.name,
                    "materials": [],
                    "delivered": []
                }
            
            # Aggregate by product for cleaner view
            balance = s.quantity - s.returned_quantity
            
            # Helper to find if prod exists in materials list
            existing = next((i for i in aggregated[w_id]["materials"] if i["product_id"] == s.product_id), None)
            
            if existing:
                existing["sent"] += s.quantity
                existing["returned"] += s.returned_quantity
                existing["balance"] += balance
            else:
                aggregated[w_id]["materials"].append({
                    "product_id": s.product_id,
                    "product": s.product.name,
                    "unit": s.product.unit,
                    "sent": s.quantity,
                    "returned": s.returned_quantity,
                    "balance": balance
                })

        # Process Delivered Production
        for m in production_movements:
            # Extract worker name from reason string: "Produção Recebida de NomeDoWorker"
            try:
                # This assumes format is constant.
                worker_name = m.reason.replace("Produção Recebida de ", "").strip()
                
                # We need a worker_id to key into 'aggregated'. 
                # This is tricky because Movement doesn't link to Worker table, only User.
                # We will key by Name if ID not found, but we started aggregated with ID.
                # Let's switch aggregation key to Worker Name for simplicity in this mixed report.
                
                # BUT wait, the loop above used ID.
                # Let's map Name -> ID? Or just use Name as key for everything?
                # Using Name as key is safer here since Movements don't have worker_id.
                pass
            except:
                continue

        # RE-STRATEGY: Aggregate by Worker Name (String)
        final_data = {}
        
        # Re-process Pending (Shipments have Worker relation, so we know name)
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
            else:
                final_data[w_name]["materials"].append({
                    "product_id": s.product_id,
                    "product": s.product.name,
                    "unit": s.product.unit,
                    "sent": s.quantity,
                    "returned": s.returned_quantity,
                    "balance": balance
                })
                
        # Process Production Movements
        for m in production_movements:
            if "Produção Recebida de " not in m.reason:
                continue
                
            w_name = m.reason.replace("Produção Recebida de ", "").strip()
            
            # Filter if worker_id was passed (safety check if names match)
            if worker_id:
                target_worker = db.query(Worker).get(worker_id)
                if target_worker and target_worker.name != w_name:
                    continue

            if w_name not in final_data:
                 final_data[w_name] = {"name": w_name, "materials": [], "delivered": []}
            
            # Aggregate Delivered Items (Finished Goods)
            existing = next((i for i in final_data[w_name]["delivered"] if i["product_id"] == m.product_id), None)
             
            if existing:
                existing["quantity"] += m.quantity
            else:
                final_data[w_name]["delivered"].append({
                    "product_id": m.product_id,
                    "product": m.product.name,
                    "unit": m.product.unit,
                    "quantity": m.quantity,
                    "last_date": m.timestamp
                })

        report_data = list(final_data.values())
        # Sort by Name
        report_data.sort(key=lambda x: x["name"])
        
        context["report_data"] = report_data
        
    elif report_type == "movements_history":
        # Global Movements History Report
        query = db.query(Movement).join(Product).order_by(Movement.timestamp.desc())

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
        query = db.query(Product)
        
        if category_id:
            query = query.filter(Product.category_id == category_id)
        if product_id:
            query = query.filter(Product.id == product_id)
            
        products = query.order_by(Product.name.asc()).all()
        context["products"] = products
        context["gen_date"] = datetime.now()

    return templates.TemplateResponse("reports.html", context)
