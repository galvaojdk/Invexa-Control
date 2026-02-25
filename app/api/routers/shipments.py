from datetime import datetime
from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.worker import Worker, Shipment, ShipmentStatus
from app.models.inventory import Product, Movement, MovementType
from app.models.production import ProductionOrder, OPStatus
from app.api.dependencies import login_required

router = APIRouter(prefix="/shipments", tags=["Shipments"])
templates = Jinja2Templates(directory="app/templates")

@router.get("")
@router.get("/")
async def shipments_view(request: Request, status_filter: str = "active", user: User = Depends(login_required), db: Session = Depends(get_db)):
    query = db.query(Shipment).filter(Shipment.company_id == user.company_id).order_by(Shipment.created_at.desc())
    
    if status_filter == "active":
        query = query.filter(Shipment.status.in_([ShipmentStatus.PENDING, ShipmentStatus.PARTIAL]))
        
    shipments = query.all()
    
    # Fetch data for modals
    workers = db.query(Worker).filter(Worker.active == True, Worker.company_id == user.company_id).all()
    products = db.query(Product).filter(Product.company_id == user.company_id).order_by(Product.name).all()
    active_ops = db.query(ProductionOrder).filter(
        ProductionOrder.company_id == user.company_id,
        ProductionOrder.status.in_([OPStatus.DRAFT, OPStatus.LIBERADA, OPStatus.IN_PROGRESS])
    ).order_by(ProductionOrder.created_at.desc()).all()

    return templates.TemplateResponse("shipments.html", {
        "request": request,
        "user": user,
        "shipments": shipments,
        "workers": workers,
        "products": products,
        "active_ops": active_ops,
        "status_filter": status_filter
    })

@router.post("/create")
async def create_shipment(
    worker_id: int = Form(...),
    product_id: int = Form(...),
    quantity: float = Form(...),
    cost_per_unit: float = Form(0.0),
    notes: str = Form(None),
    op_id: int = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(login_required)
):
    worker = db.query(Worker).filter(Worker.id == worker_id, Worker.company_id == user.company_id).first()
    product = db.query(Product).filter(Product.id == product_id, Product.company_id == user.company_id).first()
    
    if not worker or not product:
        raise HTTPException(status_code=404, detail="Recurso não encontrado")
    
    if product.current_stock < quantity:
         # TODO: flash message?
         raise HTTPException(
             status_code=400, 
             detail=f"Estoque insuficiente. Disponível: {product.current_stock} {product.unit}. Solicitado: {quantity}"
         ) 

    # Create Shipment Record
    shipment = Shipment(
        worker_id=worker.id,
        product_id=product.id,
        quantity=quantity,
        cost_per_unit=cost_per_unit,
        notes=notes,
        op_id=op_id,
        status=ShipmentStatus.PENDING,
        company_id=user.company_id
    )
    db.add(shipment)
    
    # Decrease Stock
    product.current_stock -= quantity
    
    # Log Movement
    reason_str = f"Remessa para {worker.name}"
    if op_id:
        # Fetch op to get number for log
        op = db.query(ProductionOrder).filter(ProductionOrder.id == op_id).first()
        if op:
            reason_str += f" (OP: {op.op_number})"
            # Update OP Status if it's draft or mapped
            if op.status == OPStatus.DRAFT or op.status == OPStatus.RELEASED:
                 op.status = OPStatus.IN_PROGRESS
                 
    movement = Movement(
        product_id=product.id,
        quantity=quantity,
        type=MovementType.OUT,
        reason=reason_str,
        user_id=user.id,
        company_id=user.company_id,
        sector="Terceirizado",
        timestamp=datetime.now()
    )
    db.add(movement)
    
    db.commit()
    return RedirectResponse(url="/shipments", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/{shipment_id}/return")
async def return_shipment(
    shipment_id: int,
    return_quantity: float = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(login_required)
):
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Remessa não encontrada")
    
    # Validate return quantity
    remaining = shipment.quantity - shipment.returned_quantity
    if return_quantity > remaining:
         return_quantity = remaining

    # Update Shipment
    shipment.returned_quantity += return_quantity
    shipment.updated_at = datetime.now()
    
    if shipment.returned_quantity >= shipment.quantity:
        shipment.status = ShipmentStatus.COMPLETED
    else:
        shipment.status = ShipmentStatus.PARTIAL
        
    # Increase Stock (Returns to inventory)
    shipment.product.current_stock += return_quantity
    
    # Log Movement
    movement = Movement(
        product_id=shipment.product_id,
        quantity=return_quantity,
        type=MovementType.IN,
        reason=f"Retorno de {shipment.worker.name}",
        user_id=user.id,
        company_id=user.company_id,
        sector="Estoque Principal",
        timestamp=datetime.now()
    )
    db.add(movement)
    
    db.commit()
    db.commit()
    return RedirectResponse(url="/shipments", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/{shipment_id}/cancel")
async def cancel_shipment(
    shipment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(login_required)
):
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Remessa não encontrada")
    
    # Check status
    if shipment.status not in [ShipmentStatus.PENDING, ShipmentStatus.PARTIAL]:
        # Optionally allow cancellation of COMPLETED if needed, but usually only active ones
        # For now, let's restrict to active ones to avoid complex stock logic if it was fully returned?
        # Actually, if it's COMPLETED, it means everything was returned, so nothing to cancel.
        # If it's CANCELLED, well...
        if shipment.status == ShipmentStatus.CANCELLED:
             raise HTTPException(status_code=400, detail="Remessa já cancelada")
        if shipment.status == ShipmentStatus.COMPLETED:
             raise HTTPException(status_code=400, detail="Remessa já finalizada")

    # Calculate quantity to return to stock (revoke shipment)
    # The quantity that was sent but NOT returned is effectively "out".
    # We need to put it back.
    quantity_to_restore = shipment.quantity - shipment.returned_quantity
    
    if quantity_to_restore > 0:
        shipment.product.current_stock += quantity_to_restore
        
        # Log Movement (Estorno/Cancelamento)
        movement = Movement(
            product_id=shipment.product_id,
            quantity=quantity_to_restore,
            type=MovementType.IN,
            reason=f"Cancelamento de remessa para {shipment.worker.name}",
            user_id=user.id,
            company_id=user.company_id,
            sector="Estoque Principal",
            timestamp=datetime.now()
        )
        db.add(movement)

    # Update Shipment Status
    shipment.status = ShipmentStatus.CANCELLED
    shipment.updated_at = datetime.now()
    
    db.commit()
    return RedirectResponse(url="/shipments", status_code=status.HTTP_303_SEE_OTHER)
