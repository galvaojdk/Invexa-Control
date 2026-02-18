from datetime import date, timedelta, datetime
from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import SessionLocal
from app.models.user import User
from app.models.inventory import Product, Category, Movement, MovementType, ProductComposition
from app.models.worker import Worker, Shipment, ShipmentStatus
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

        # Active Shipments Count
        active_shipments_count = db.query(Shipment).filter(
            Shipment.status.in_([ShipmentStatus.PENDING, ShipmentStatus.PARTIAL])
        ).count()

        # Pending Receive Quantity (Theorical Production / Kits)
        # Instead of summing raw materials, we calculate how many finished goods can be made.
        
        # 1. Fetch all active shipments
        active_shipments = db.query(Shipment).filter(
            Shipment.status.in_([ShipmentStatus.PENDING, ShipmentStatus.PARTIAL])
        ).all()
        
        # 2. Group by Worker
        from collections import defaultdict
        worker_materials = defaultdict(lambda: defaultdict(float))
        for s in active_shipments:
            balance = s.quantity - (s.returned_quantity or 0)
            if balance > 0:
                worker_materials[s.worker_id][s.product_id] += balance
                
        # 3. Fetch Recipes (Compositions)
        compositions = db.query(ProductComposition).all()
        recipes = defaultdict(dict)
        for comp in compositions:
            recipes[comp.composite_id][comp.component_id] = comp.quantity
            
        pending_receive_qty = 0
        
        # 4. Calculate Max Yield per Worker
        for w_id, materials in worker_materials.items():
            possible_products = 0
            # Check against all known recipes
            for prod_id, recipe in recipes.items():
                max_units = float('inf')
                has_components = False
                
                for comp_id, req_qty in recipe.items():
                    available = materials.get(comp_id, 0)
                    if available > 0:
                        has_components = True
                    
                    if req_qty > 0:
                        max_units = min(max_units, available / req_qty)
                    else:
                        max_units = 0
                
                if has_components and max_units != float('inf'):
                    # We assume the worker is making this product. 
                    # If multiple recipes match, this simple logic sums them (which might be wrong if materials shared),
                    # but for now it satisfies the user's "Kit" requirement.
                    possible_products += int(max_units)
                    
            pending_receive_qty += possible_products

        # If 0 pending products but we have active shipments, maybe fallback to raw count?
        # User explicitly complained about raw count. So let's stick to 0 if no full kit is possible.
        # Or maybe show 0 to indicate "Missing parts".

        
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
        
        # Worker Consumption (Top 5 in last 30 days)
        # Based on Shipments created (sent materials)
        recent_shipments_in = db.query(Shipment).filter(
            Shipment.created_at >= thirty_days_ago
        ).all()
        
        worker_consumption_raw = {}
        total_out_qty = 0
        
        for s in recent_shipments_in:
            worker_name = s.worker.name
            worker_consumption_raw[worker_name] = worker_consumption_raw.get(worker_name, 0) + s.quantity
            total_out_qty += s.quantity

        # Sort by quantity desc
        worker_consumption = dict(sorted(worker_consumption_raw.items(), key=lambda item: item[1], reverse=True)[:5])

        # Top Produced Products (Top 5 in last 30 days)
        # Based on Shipments updated (returned materials) - ONLY COMPOSITE PRODUCTS
        recent_shipments_out = db.query(Shipment).join(Product).filter(
            Shipment.updated_at >= thirty_days_ago,
            Shipment.returned_quantity > 0,
            Product.is_composite == True
        ).all()
        
        production_raw = {}
        total_produced_qty = 0
        
        for s in recent_shipments_out:
            prod_name = s.product.name
            production_raw[prod_name] = production_raw.get(prod_name, 0) + s.returned_quantity
            total_produced_qty += s.returned_quantity
            
        top_production = dict(sorted(production_raw.items(), key=lambda item: item[1], reverse=True)[:5])

        # Fetch all products ordered by name for quick actions/modals
        all_products = db.query(Product).order_by(Product.name).all()

        stats = {
            "total_products": total_products,
            "total_categories": total_categories,
            "total_workers": total_workers,
            "movements_today": movements_today,
            "active_shipments": active_shipments_count,
            "pending_receive": pending_receive_qty
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
            "cat_counts": category_counts,
            "worker_consumption": worker_consumption,
            "top_production": top_production,
            "recent_count": recent_count,
            "total_out_qty": total_out_qty,
            "total_produced_qty": total_produced_qty
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
            "sector_consumption": {}, # Keep empty for compatibility if template not updated yet
            "worker_consumption": {}, 
            "top_production": {},
            "recent_count": 0,
            "total_out_qty": 0,
            "total_produced_qty": 0
        })
