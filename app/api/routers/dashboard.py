from datetime import date, timedelta, datetime
from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import SessionLocal
from app.models.user import User
from app.models.inventory import Product, Category, Movement, MovementType
from app.models.worker import Worker
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
        # low_stock removed as per request
        
        today = date.today()
        # Use range query for movements_today which is DB-agnostic and index-friendly
        start_of_day = datetime.combine(today, datetime.min.time())
        end_of_day = datetime.combine(today, datetime.max.time())
        
        movements_today = db.query(Movement).filter(
            Movement.timestamp >= start_of_day,
            Movement.timestamp <= end_of_day
        ).count()
        
        total_categories = db.query(Category).count()
        total_workers = db.query(Worker).count()
        
        # Latest Movements
        latest_movements = db.query(Movement).order_by(Movement.timestamp.desc()).limit(10).all()
        
        # Chart Data: Movements Last 7 Days
        seven_days_ago = today - timedelta(days=6)
        # Use func.date() for grouping by date which works on both SQLite and Postgres
        # On Postgres it returns Date object, on SQLite string YYYY-MM-DD
        daily_movements = db.query(
            func.date(Movement.timestamp).label('date'),
            Movement.type,
            func.sum(Movement.quantity).label('total')
        ).filter(
            Movement.timestamp >= datetime.combine(seven_days_ago, datetime.min.time())
        ).group_by(
            func.date(Movement.timestamp), Movement.type
        ).all()
        
        # Process data for Chart.js
        dates = [(seven_days_ago + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]
        entries_data = [0] * 7
        exits_data = [0] * 7
        
        # Normalizing date keys to string for map lookup
        movement_map = {}
        for row in daily_movements:
            d_str = str(row.date) # row.date could be date object or string depending on DB
            movement_map[(d_str, row.type)] = row.total
        
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


        
        # Additional Dashboard Metrics (moved from Reports)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        recent_movements = db.query(Movement).filter(Movement.timestamp >= thirty_days_ago).all()
        recent_count = len(recent_movements)
        
        sector_consumption_raw = {}
        total_out_qty = 0
        for m in recent_movements:
            if m.type == MovementType.OUT:
                sec = m.sector or "Não Definido"
                sector_consumption_raw[sec] = sector_consumption_raw.get(sec, 0) + m.quantity
                total_out_qty += m.quantity
                
        # Sort sector consumption by quantity desc
        sector_consumption = dict(sorted(sector_consumption_raw.items(), key=lambda item: item[1], reverse=True)[:5])

        # Fetch all products ordered by name for quick actions/modals
        all_products = db.query(Product).order_by(Product.name).all()

        stats = {
            "total_products": total_products,
            "total_categories": total_categories,
            "total_workers": total_workers,
            "movements_today": movements_today
        }
        
        return templates.TemplateResponse("dashboard.html", {
            "request": request, 
            "user": user, 
            "stats": stats,
            "products": all_products, # Pass full products list for Quick Actions
            "latest_movements": latest_movements,
            "chart_dates": dates,
            "chart_entries": entries_data,
            "chart_exits": exits_data,
            "cat_labels": category_labels,
            "cat_counts": category_counts,
            "sector_consumption": sector_consumption,
            "recent_count": recent_count,
            "total_out_qty": total_out_qty
        })
    except Exception as e:
        logger.error(f"DASHBOARD ERROR: {str(e)}", exc_info=True)
        # In a real app, use logger
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "user": user,
            "error": "Erro ao carregar dados do dashboard.",
            "stats": {"total_products": 0, "movements_today": 0, "total_categories": 0, "total_workers": 0},
            "latest_movements": [],
            "chart_dates": [],
            "chart_entries": [],
            "chart_exits": [],
            "cat_labels": [],
            "cat_counts": [],
            "sector_consumption": {},
            "recent_count": 0,
            "total_out_qty": 0
        })
