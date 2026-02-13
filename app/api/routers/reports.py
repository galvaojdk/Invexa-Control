from datetime import datetime, timedelta
from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.models.inventory import Product, Movement, MovementType
from app.models.user import User
from app.api.dependencies import get_db, login_required

router = APIRouter(prefix="/reports", tags=["Reports"])
templates = Jinja2Templates(directory="app/templates")

from app.models.worker import Shipment, Worker

@router.get("")
@router.get("/")
async def reports_view(
    request: Request,
    report_type: str = "stock",
    start_date: str = None,
    end_date: str = None,
    user: User = Depends(login_required),
    db: Session = Depends(get_db)
):
    # Common context
    context = {
        "request": request,
        "user": user,
        "report_type": report_type
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
        
    elif report_type == "movements_history":
        # Global Movements History Report
        query = db.query(Movement).order_by(Movement.timestamp.desc())

        if filter_start:
            query = query.filter(Movement.timestamp >= filter_start)
        if filter_end:
            query = query.filter(Movement.timestamp <= filter_end)
            
        # Limit only if no filter (or very loose filter) to prevent massive scan
        if not filter_start:
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
        # Stock is always snapshot logic, filters typically don't apply to "current stock" unless historical reconstruction
        products = db.query(Product).order_by(Product.name.asc()).all()
        context["products"] = products
        context["gen_date"] = datetime.now()

    return templates.TemplateResponse("reports.html", context)
