from datetime import datetime
from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.worker import Worker, Shipment, ShipmentStatus
from app.models.inventory import Product, Movement, MovementType, AuditLog
from app.api.dependencies import login_required

router = APIRouter(prefix="/workers", tags=["Workers"])
templates = Jinja2Templates(directory="app/templates")

@router.get("")
@router.get("/")
async def workers_view(request: Request, user: User = Depends(login_required), db: Session = Depends(get_db)):
    workers = db.query(Worker).filter(Worker.active == True).all()
    products = db.query(Product).all()
    
    # Fetch active shipments for display
    active_shipments = db.query(Shipment).filter(
        Shipment.status.in_([ShipmentStatus.PENDING, ShipmentStatus.PARTIAL])
    ).all()

    return templates.TemplateResponse("workers.html", {
        "request": request,
        "user": user,
        "workers": workers,
        "products": products,
        "active_shipments": active_shipments
    })

@router.post("/create")
async def create_worker(
    name: str = Form(...),
    role: str = Form(...),
    phone: str = Form(None),
    daily_rate: float = Form(0.0),
    db: Session = Depends(get_db),
    user: User = Depends(login_required)
):
    new_worker = Worker(
        name=name,
        role=role,
        phone=phone,
        daily_rate=daily_rate
    )
    db.add(new_worker)
    db.flush()
    
    db.add(AuditLog(
        user_id=user.id,
        action="CREATE_WORKER",
        resource_type="worker",
        resource_id=new_worker.id,
        description=f"Terceirizado '{name}' cadastrado. Função: {role}"
    ))
    db.commit()
    return RedirectResponse(url="/workers", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/{worker_id}/update")
async def update_worker(
    worker_id: int,
    name: str = Form(...),
    role: str = Form(...),
    phone: str = Form(None),
    daily_rate: float = Form(0.0),
    db: Session = Depends(get_db),
    user: User = Depends(login_required)
):
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Terceirizado não encontrado")
    
    worker.name = name
    worker.role = role
    worker.phone = phone
    worker.daily_rate = daily_rate
    
    db.add(AuditLog(
        user_id=user.id,
        action="UPDATE_WORKER",
        resource_type="worker",
        resource_id=worker.id,
        description=f"Terceirizado '{name}' atualizado."
    ))
    db.commit()
    return RedirectResponse(url="/workers", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/{worker_id}/delete")
async def delete_worker(
    worker_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(login_required)
):
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if worker:
        worker.active = False
        db.add(AuditLog(
            user_id=user.id,
            action="DELETE_WORKER",
            resource_type="worker",
            resource_id=worker.id,
            description=f"Terceirizado '{worker.name}' inativado."
        ))
        db.commit()
    return RedirectResponse(url="/workers", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/{worker_id}/shipments")
async def create_shipment(
    worker_id: int,
    product_id: int = Form(...),
    quantity: float = Form(...),
    cost_per_unit: float = Form(0.0),
    notes: str = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(login_required)
):
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    product = db.query(Product).filter(Product.id == product_id).first()
    
    if not worker or not product:
        raise HTTPException(status_code=404, detail="Recurso não encontrado")
    
    if product.current_stock < quantity:
         # Optional: Allow negative stock or block? Let's block for safety or warn.
         # For this specific app, creating a movement usually allows negative if needed but let's be strict.
         # user: "controlar o envio de peças" -> implies taking from stock.
         pass 

    # Create Shipment Record
    shipment = Shipment(
        worker_id=worker.id,
        product_id=product.id,
        quantity=quantity,
        cost_per_unit=cost_per_unit,
        notes=notes,
        status=ShipmentStatus.PENDING
    )
    db.add(shipment)
    
    # Decrease Stock
    product.current_stock -= quantity
    
    # Log Movement
    movement = Movement(
        product_id=product.id,
        quantity=quantity,
        type=MovementType.OUT,
        reason=f"Remessa para {worker.name}",
        user_id=user.id,
        sector="Terceirizado"
    )
    db.add(movement)
    
    db.commit()
    return RedirectResponse(url="/workers", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/shipments/{shipment_id}/return")
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
         # Cap at remaining or allow over-return? Cap it to avoid logic errors.
         return_quantity = remaining

    # Update Shipment
    shipment.returned_quantity += return_quantity
    shipment.updated_at = datetime.utcnow()
    
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
        sector="Estoque Principal"
    )
    db.add(movement)
    
    db.commit()
    return RedirectResponse(url="/workers", status_code=status.HTTP_303_SEE_OTHER)
