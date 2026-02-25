import os
from datetime import date
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import SessionLocal, Base, engine

from app.models.company import Company
from app.models.user import User
from app.models.inventory import Product, Category, Movement
from app.models.ticket import SupportTicket, TicketMessage
from app.api.dependencies import get_db, login_required
from app.api.routers import auth, inventory, movements, admin, reports
from app.models.worker import Worker, Shipment
from app.models.production import ProductionOrder, OPMaterial
from app.models.system import SystemGuide
from app.core.init_db import init_multitenancy

# Create tables on startup
Base.metadata.create_all(bind=engine)

from sqlalchemy import text
with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE ticket_messages ADD COLUMN is_read BOOLEAN DEFAULT FALSE"))
        conn.commit()
    except Exception:
        conn.rollback()
    
    try:
        conn.execute(text("ALTER TABLE shipments ADD COLUMN op_id INTEGER REFERENCES production_orders(id)"))
        conn.commit()
    except Exception:
        conn.rollback()

    try:
        conn.execute(text("ALTER TABLE production_orders ADD COLUMN completed_at DATETIME"))
        conn.commit()
    except Exception:
        conn.rollback()

    try:
        conn.execute(text("ALTER TABLE users ADD COLUMN guide_version_viewed INTEGER DEFAULT 0"))
        conn.commit()
    except Exception:
        conn.rollback()

# Initialize multi-tenancy (ensure demo company and migrate orphaned data)
db = SessionLocal()
try:
    init_multitenancy(db)
finally:
    db.close()

app = FastAPI(title="Invexa Control")

# Static files and Templates
if not os.path.exists("app/static"):
    os.makedirs("app/static")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# --- MIDDLEWARES & ERROR HANDLERS ---

@app.middleware("http")
async def log_requests(request: Request, call_next):
    # Professional logging here (simplified for demo)
    return await call_next(request)

@app.exception_handler(404)
async def not_found_exception_handler(request: Request, exc: HTTPException):
    accept_header = request.headers.get("accept", "")
    if "text/html" in accept_header:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
    return JSONResponse(status_code=404, content={"detail": "Recurso não encontrado"})

# --- INCLUDE ROUTERS ---
app.include_router(auth.router)
app.include_router(inventory.router)
app.include_router(movements.router)

app.include_router(admin.router)
app.include_router(reports.router)
from app.api.routers import support
app.include_router(support.router)
from app.api.routers import workers
app.include_router(workers.router)
from app.api.routers import dashboard
app.include_router(dashboard.router)
from app.api.routers import shipments
app.include_router(shipments.router)
from app.api.routers import production
app.include_router(production.router)
from app.api.routers import system_guide
app.include_router(system_guide.router)

@app.get("/")
async def root():
    return RedirectResponse(url="/dashboard")

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/premium/subscribe")
async def premium_view(request: Request, user: User = Depends(login_required)):
    return templates.TemplateResponse("premium_sub.html", {"request": request, "user": user})
