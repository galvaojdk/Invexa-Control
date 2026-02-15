from datetime import datetime
from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.models.inventory import Product, Movement, MovementType
from app.models.user import User
from app.models.worker import Worker
from app.api.dependencies import get_db, login_required
from app.services.inventory_service import InventoryService

router = APIRouter(prefix="/movements", tags=["Movements"])
templates = Jinja2Templates(directory="app/templates")

@router.get("")
@router.get("/")
async def movements_view(request: Request, user: User = Depends(login_required), db: Session = Depends(get_db)):
    movements_list = db.query(Movement).order_by(Movement.timestamp.desc()).all()
    products = db.query(Product).all()
    workers = db.query(Worker).filter(Worker.active == True).all()
    return templates.TemplateResponse("movements.html", {
        "request": request, 
        "user": user, 
        "movements": movements_list,
        "products": products,
        "workers": workers
    })

@router.post("")
@router.post("/")
async def register_movement(
    product_id: int = Form(...),
    quantity: float = Form(...),
    mov_type: str = Form(..., alias="type"),
    reason: str = Form(None),
    sector: str = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(login_required)
):
    # Normalize input
    mov_type_str = mov_type.lower().strip()
    m_type = MovementType.IN if mov_type_str == "entrada" else MovementType.OUT
    
    try:
        # Using Centralized Service!
        InventoryService.register_stock_movement(
            db=db,
            product_id=product_id,
            quantity=quantity,
            mov_type=m_type,
            user_id=user.id,
            reason=reason,
            sector=sector
        )
        db.commit()
    except ValueError as e:
        # Estoque insuficiente é um erro de validação (Bad Request), não "Não Encontrado"
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao registrar movimentação: {str(e)}")
        
    return RedirectResponse(url="/movements", status_code=303)

@router.get("/api/v1/products/{product_id}")
async def get_product_details_api(
    product_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(login_required)
):
    """
    Relocated from main.py, keeping original structure for frontend compatibility.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
        
    history = db.query(Movement).filter(Movement.product_id == product_id).order_by(Movement.timestamp.desc()).limit(10).all()
    
    return {
        "id": product.id,
        "sku": product.sku,
        "name": product.name,
        "description": product.description,
        "category": product.category.name if product.category else "-",
        "unit": product.unit or "un",
        "current_stock": product.current_stock,
        "min_stock": product.min_stock,
        "is_composite": product.is_composite,
        "is_primary": product.is_primary,
        "history": [
            {
                "type": m.type.value,
                "quantity": m.quantity,
                "reason": m.reason,
                "sector": m.sector or "-",
                "timestamp": m.timestamp.strftime("%d/%m/%Y %H:%M")
            } for m in history
        ]
    }
