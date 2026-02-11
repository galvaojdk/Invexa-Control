from datetime import datetime, timedelta
from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.models.inventory import Product, Movement, MovementType
from app.models.user import User
from app.api.dependencies import get_db, login_required

router = APIRouter(prefix="/reports", tags=["Reports"])
templates = Jinja2Templates(directory="app/templates")

@router.get("")
@router.get("/")
async def reports_view(
    request: Request,
    user: User = Depends(login_required),
    db: Session = Depends(get_db)
):
    products = db.query(Product).order_by(Product.name.asc()).all()
    critical_items = [p for p in products if p.current_stock <= p.min_stock]
    
    thirty_days_ago = datetime.now() - timedelta(days=30)
    recent_movements = db.query(Movement).filter(Movement.timestamp >= thirty_days_ago).all()
    
    sector_consumption = {}
    for m in recent_movements:
        if m.type == MovementType.OUT:
            sec = m.sector or "Não Definido"
            sector_consumption[sec] = sector_consumption.get(sec, 0) + m.quantity
            
    return templates.TemplateResponse("reports.html", {
        "request": request,
        "user": user,
        "products": products,
        "critical_count": len(critical_items),
        "recent_count": len(recent_movements),
        "sector_consumption": sector_consumption
    })
