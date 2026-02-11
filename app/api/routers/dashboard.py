from datetime import date, timedelta
from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import SessionLocal
from app.models.user import User
from app.models.inventory import Product, Category, Movement, MovementType
from app.api.dependencies import get_db, login_required

import logging

router = APIRouter(tags=["Dashboard"])
templates = Jinja2Templates(directory="app/templates")
logger = logging.getLogger(__name__)

@router.get("/")
@router.get("/dashboard")
async def dashboard_view(request: Request, user: User = Depends(login_required), db: Session = Depends(get_db)):
    try:
        # Basic Stats
        total_products = db.query(Product).count()
        low_stock = db.query(Product).filter(Product.current_stock <= Product.min_stock).count()
        today = date.today()
        movements_today = db.query(Movement).filter(func.strftime('%Y-%m-%d', Movement.timestamp) == today.strftime('%Y-%m-%d')).count()
        total_categories = db.query(Category).count()
        
        # Latest Movements
        latest_movements = db.query(Movement).order_by(Movement.timestamp.desc()).limit(10).all()
        
        # Chart Data: Movements Last 7 Days
        seven_days_ago = today - timedelta(days=6)
        daily_movements = db.query(
            func.strftime('%Y-%m-%d', Movement.timestamp).label('date'),
            Movement.type,
            func.sum(Movement.quantity).label('total')
        ).filter(
            Movement.timestamp >= seven_days_ago
        ).group_by(
            'date', Movement.type
        ).all()
        
        # Process data for Chart.js
        dates = [(seven_days_ago + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]
        entries_data = [0] * 7
        exits_data = [0] * 7
        
        movement_map = {(row.date, row.type): row.total for row in daily_movements}
        
        for i, d in enumerate(dates):
            entries_data[i] = movement_map.get((d, MovementType.IN), 0)
            exits_data[i] = movement_map.get((d, MovementType.OUT), 0)
            
        # Chart Data: Products by Category
        cat_data = db.query(
            Category.name,
            func.count(Product.id).label('count')
        ).join(Product).group_by(Category.name).all()
        
        category_labels = [c.name for c in cat_data]
        category_counts = [c.count for c in cat_data]

        stats = {
            "total_products": total_products,
            "low_stock": low_stock,
            "movements_today": movements_today,
            "total_categories": total_categories
        }
        
        return templates.TemplateResponse("dashboard.html", {
            "request": request, 
            "user": user, 
            "stats": stats,
            "latest_movements": latest_movements,
            "chart_dates": dates,
            "chart_entries": entries_data,
            "chart_exits": exits_data,
            "cat_labels": category_labels,
            "cat_counts": category_counts
        })
    except Exception as e:
        logger.error(f"DASHBOARD ERROR: {str(e)}", exc_info=True)
        # In a real app, use logger
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "user": user,
            "error": "Erro ao carregar dados do dashboard.",
            "stats": {"total_products": 0, "low_stock": 0, "movements_today": 0, "total_categories": 0},
            "latest_movements": [],
            "chart_dates": [],
            "chart_entries": [],
            "chart_exits": [],
            "cat_labels": [],
            "cat_counts": []
        })
