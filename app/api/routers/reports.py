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
        # Review Report: Items currently with workers (Balance > 0)
        query = db.query(Shipment).join(Worker).join(Product)\
            .filter(Shipment.status != ShipmentStatus.CANCELLED)\
            .filter(Shipment.quantity > Shipment.returned_quantity)\
            .order_by(Worker.name, Product.name)
            
        if filter_start:
             query = query.filter(Shipment.created_at >= filter_start)
        if filter_end:
             query = query.filter(Shipment.created_at <= filter_end)
        if worker_id:
             query = query.filter(Shipment.worker_id == worker_id)
        if product_id:
             query = query.filter(Shipment.product_id == product_id)
             
        shipments = query.all()
        
        # Aggregate by Worker
        # Structure: { worker_id: { name: str, items: [ { product, sent, returned, balance, date } ] } }
        aggregated = {}
        
        for s in shipments:
            if s.worker_id not in aggregated:
                aggregated[s.worker_id] = {
                    "name": s.worker.name,
                    "items": []
                }
            
            # Check if product already exists for this worker to merge (optional, but shipments are usually distinct records)
            # User might want to see individual shipments or total per product. 
            # Usually "what he has" implies total per product. Let's aggregate per product per worker.
            
            existing_item = next((i for i in aggregated[s.worker_id]["items"] if i["product_id"] == s.product_id), None)
            
            balance = s.quantity - s.returned_quantity
            
            if existing_item:
                existing_item["sent"] += s.quantity
                existing_item["returned"] += s.returned_quantity
                existing_item["balance"] += balance
                # Keep checking latest date?
            else:
                aggregated[s.worker_id]["items"].append({
                    "product_id": s.product_id,
                    "product": s.product.name,
                    "unit": s.product.unit,
                    "sent": s.quantity,
                    "returned": s.returned_quantity,
                    "balance": balance
                })
        
        # Convert to list for template
        report_data = list(aggregated.values())
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
