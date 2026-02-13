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
    user: User = Depends(login_required),
    db: Session = Depends(get_db)
):
    # Common context
    context = {
        "request": request,
        "user": user,
        "report_type": report_type
    }

    if report_type == "outsourced":
        # Fetch data for Outsourced Shipments Report
        # Order by date desc
        shipments = db.query(Shipment).order_by(Shipment.created_at.desc()).all()
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
        
    else: # Default: 'stock'
        # Stock Position Report
        products = db.query(Product).order_by(Product.name.asc()).all()
        context["products"] = products
        context["gen_date"] = datetime.now()

    return templates.TemplateResponse("reports.html", context)
