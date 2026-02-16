from datetime import datetime
from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.models.inventory import Product, Movement, MovementType
from app.models.user import User
from app.models.worker import Worker, Shipment, ShipmentStatus
from app.api.dependencies import get_db, login_required
from app.services.inventory_service import InventoryService
from pydantic import BaseModel
from typing import List, Optional

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
        # Stock validation error - Redirect with error message
        return RedirectResponse(
            url=f"/movements?error={str(e)}", 
            status_code=303
        )
    except Exception as e:
        db.rollback()
        # General error - Redirect with error message
        return RedirectResponse(
            url=f"/movements?error=Erro ao registrar movimentação: {str(e)}", 
            status_code=303
        )
        
    return RedirectResponse(url="/movements", status_code=303)

class MovementItem(BaseModel):
    product_id: int
    quantity: float

class BatchMovementRequest(BaseModel):
    type: str # 'entrada' or 'saida'
    reason: Optional[str] = None
    sector: Optional[str] = None
    items: List[MovementItem]

@router.post("/batch")
async def register_batch_movements(
    data: BatchMovementRequest,
    db: Session = Depends(get_db),
    user: User = Depends(login_required)
):
    mov_type_str = data.type.lower().strip()
    m_type = MovementType.IN if mov_type_str == "entrada" else MovementType.OUT
    
    try:
        success_count = 0
        created_movements = []
        for item in data.items:
            # Check for worker context
            final_sector = data.sector
            worker_id = None
            
            if data.sector and data.sector.startswith("WORKER:"):
                parts = data.sector.split(":")
                if len(parts) >= 3:
                    worker_id = int(parts[1])
                    worker_name = parts[2]
                    final_sector = f"Terceirizado: {worker_name}"

            # Using Centralized Service!
            movement = InventoryService.register_stock_movement(
                db=db,
                product_id=item.product_id,
                quantity=item.quantity,
                mov_type=m_type,
                user_id=user.id,
                reason=data.reason,
                sector=final_sector
            )
            created_movements.append(movement)

            # If it's an OUT going to a WORKER, create a SHIPMENT record
            if m_type == MovementType.OUT and worker_id:
                new_shipment = Shipment(
                    worker_id=worker_id,
                    product_id=item.product_id,
                    quantity=item.quantity,
                    status=ShipmentStatus.PENDING,
                    notes=data.reason
                )
                db.add(new_shipment)

            success_count += 1
            
        db.commit()
        
        # Return IDs for printing
        movement_ids = [m.id for m in created_movements]
        
        return {
            "message": f"{success_count} itens processados com sucesso", 
            "count": success_count,
            "movement_ids": movement_ids
        }
        
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.get("/print/batch")
async def print_batch_packing_list(
    ids: str,
    db: Session = Depends(get_db),
    user: User = Depends(login_required)
):
    """
    Generates a printable packing list (Romaneio) for a set of movement IDs.
    Expects ids as a comma-separated string, e.g., ?ids=1,2,3
    """
    try:
        id_list = [int(id_str) for id_str in ids.split(",") if id_str.strip().isdigit()]
        if not id_list:
             raise HTTPException(status_code=400, detail="Nenhum ID fornecido")
             
        movements = db.query(Movement).filter(Movement.id.in_(id_list)).all()
        
        if not movements:
            raise HTTPException(status_code=404, detail="Nenhuma movimentação encontrada")
            
        # Group by sector/destination if possible, or just take the first one
        # Assuming batch movements share the same sector/destination context
        sector = movements[0].sector if movements else "N/A"
        reason = movements[0].reason if movements else "N/A"
        date = movements[0].timestamp
        
        return templates.TemplateResponse("packing_list.html", {
            "request": {}, # minimal mock request if needed by template, or just pass nothing if not used
            "user": user,
            "movements": movements,
            "sector": sector,
            "reason": reason,
            "date": date,
            "total_items": len(movements)
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
