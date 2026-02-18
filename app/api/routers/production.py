from fastapi import APIRouter, Depends, HTTPException, status, Form
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from app.api.dependencies import get_db, login_required
from app.models.user import User
from app.models.inventory import Product, Movement, MovementType, ProductComposition
from app.models.worker import Worker, Shipment, ShipmentStatus

router = APIRouter(prefix="/production", tags=["Production"])

@router.post("/register")
async def register_production(
    worker_id: int = Form(...),
    product_id: int = Form(...),
    quantity: float = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(login_required)
):
    # 1. Validate Worker and Product
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Terceirizado não encontrado")
        
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
        
    if quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantidade deve ser maior que zero")

    # 2. Check Composition
    if not product.is_composite:
         # Optionally allow receiving non-composite products (just simple entry?), 
         # but for this feature ("Retorno de Produção"), we focus on composite.
         # Or maybe user just wants to register they made something even if not composite?
         # For now, let's assume it MUST be composite to trigger component deduction.
         pass 

    components = db.query(ProductComposition).filter(ProductComposition.composite_id == product_id).all()
    
    if not components and product.is_composite:
         raise HTTPException(status_code=400, detail="Produto marcado como composto mas sem composição definida.")

    warnings = []
    
    # 3. Deduct Components from Worker's Shipments (FIFO)
    for comp in components:
        required_qty = quantity * comp.quantity
        component_product = comp.component
        
        # Find active shipments for this component and worker
        # Order by created_at ASC (FIFO)
        shipments = db.query(Shipment).filter(
            Shipment.worker_id == worker_id,
            Shipment.product_id == comp.component_id,
            Shipment.status.in_([ShipmentStatus.PENDING, ShipmentStatus.PARTIAL]),
            (Shipment.quantity - Shipment.returned_quantity) > 0 # Has balance
        ).order_by(Shipment.created_at.asc()).all()
        
        remaining_to_deduct = required_qty
        
        for shipment in shipments:
            balance = shipment.quantity - shipment.returned_quantity
            
            if remaining_to_deduct <= 0:
                break
                
            deduct_amount = min(remaining_to_deduct, balance)
            
            # Update Shipment
            shipment.returned_quantity += deduct_amount
            
            # Update Status
            if shipment.returned_quantity >= shipment.quantity:
                shipment.status = ShipmentStatus.COMPLETED
            else:
                shipment.status = ShipmentStatus.PARTIAL
                
            remaining_to_deduct -= deduct_amount
            
        if remaining_to_deduct > 0:
            warnings.append(f"Atencao: Saldo insuficiente de '{component_product.name}' com {worker.name}. Faltou baixar {remaining_to_deduct} {component_product.unit}.")

    # 4. Register Entry Movement for Finished Good
    movement = Movement(
        product_id=product_id,
        quantity=quantity,
        type=MovementType.IN,
        reason=f"Produção Recebida de {worker.name}",
        user_id=user.id,
        timestamp=datetime.now()
    )
    db.add(movement)
    
    # Update Finished Good Stock
    product.current_stock += quantity
    
    db.commit()
    
    if warnings:
        # Return success but with warnings
        # Since we use Form post, usually we redirect. 
        # But if we use AJAX (which is better for modals), we return JSON.
        # Let's assume AJAX call from frontend.
        return JSONResponse(content={"message": "Produção registrada com sucesso!", "warnings": warnings}, status_code=200)

    return JSONResponse(content={"message": "Produção registrada com sucesso!"}, status_code=200)
