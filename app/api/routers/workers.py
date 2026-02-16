from datetime import datetime
from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.worker import Worker, Shipment, ShipmentStatus
from app.models.worker_type import WorkerType
from app.models.inventory import Product, Movement, MovementType, AuditLog
from app.api.dependencies import login_required

router = APIRouter(prefix="/workers", tags=["Workers"])
templates = Jinja2Templates(directory="app/templates")

@router.post("/types/create")
async def create_worker_type(
    name: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(login_required)
):
    existing = db.query(WorkerType).filter(WorkerType.name == name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Tipo já existe")
    
    new_type = WorkerType(name=name)
    db.add(new_type)
    db.commit()
    
    return RedirectResponse(url="/workers", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/types/{type_id}/update")
async def update_worker_type(
    type_id: int,
    name: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(login_required)
):
    worker_type = db.query(WorkerType).filter(WorkerType.id == type_id).first()
    if not worker_type:
        raise HTTPException(status_code=404, detail="Tipo não encontrado")
    
    worker_type.name = name
    db.commit()
    return RedirectResponse(url="/workers", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/types/{type_id}/delete")
async def delete_worker_type(
    type_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(login_required)
):
    worker_type = db.query(WorkerType).filter(WorkerType.id == type_id).first()
    if not worker_type:
        raise HTTPException(status_code=404, detail="Tipo não encontrado")
    
    # Check for dependent workers
    dependent_count = db.query(Worker).filter(Worker.worker_type_id == type_id, Worker.active == True).count()
    if dependent_count > 0:
         # TODO: Handle error gracefully in frontend (flash message?), for now raising HTTP exception
         raise HTTPException(status_code=400, detail=f"Não é possível excluir. Existem {dependent_count} terceirizados vinculados a este tipo.")

    db.delete(worker_type)
    db.commit()
    return RedirectResponse(url="/workers", status_code=status.HTTP_303_SEE_OTHER)

@router.get("")
@router.get("/")
async def workers_view(request: Request, user: User = Depends(login_required), db: Session = Depends(get_db)):
    workers = db.query(Worker).filter(Worker.active == True).all()
    products = db.query(Product).all()
    worker_types = db.query(WorkerType).all()
    
    # Fetch active shipments for display
    active_shipments = db.query(Shipment).filter(
        Shipment.status.in_([ShipmentStatus.PENDING, ShipmentStatus.PARTIAL])
    ).all()

    return templates.TemplateResponse("workers.html", {
        "request": request,
        "user": user,
        "workers": workers,
        "products": products,
        "worker_types": worker_types,
        "active_shipments": active_shipments
    })

@router.post("/create")
async def create_worker(
    name: str = Form(...),
    address: str = Form(None),
    zip_code: str = Form(None),
    worker_type_id: int = Form(...),
    phone: str = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(login_required)
):
    worker_type = db.query(WorkerType).filter(WorkerType.id == worker_type_id).first()
    role_name = worker_type.name if worker_type else "Desconhecido"

    new_worker = Worker(
        name=name,
        address=address,
        zip_code=zip_code,
        worker_type_id=worker_type_id,
        phone=phone,
        role=role_name # Keeping role populated for backward compatibility/logging if needed
    )
    db.add(new_worker)
    db.flush()
    
    db.add(AuditLog(
        user_id=user.id,
        action="CREATE_WORKER",
        resource_type="worker",
        resource_id=new_worker.id,
        description=f"Terceirizado '{name}' cadastrado. Tipo: {role_name}"
    ))
    db.commit()
    return RedirectResponse(url="/workers", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/{worker_id}/update")
async def update_worker(
    worker_id: int,
    name: str = Form(...),
    address: str = Form(None),
    zip_code: str = Form(None),
    worker_type_id: int = Form(...),
    phone: str = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(login_required)
):
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Terceirizado não encontrado")
    
    worker.name = name
    worker.address = address
    worker.zip_code = zip_code
    worker.worker_type_id = worker_type_id
    worker.phone = phone
    
    # Update deprecated role field just in case
    worker_type = db.query(WorkerType).filter(WorkerType.id == worker_type_id).first()
    if worker_type:
        worker.role = worker_type.name

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
    if not worker:
        raise HTTPException(status_code=404, detail="Terceirizado não encontrado")

    # Check for existing shipments
    shipment_count = db.query(Shipment).filter(Shipment.worker_id == worker_id).count()
    if shipment_count > 0:
        return RedirectResponse(
            url=f"/workers?error=Não é possível excluir. Existem {shipment_count} remessas vinculadas a este terceirizado.",
            status_code=status.HTTP_303_SEE_OTHER
        )

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
