from fastapi import APIRouter, Depends, HTTPException, status, Form, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from app.api.dependencies import get_db, login_required
from app.models.user import User
from app.models.inventory import Product, Movement, MovementType, ProductComposition
from app.models.worker import Worker, Shipment, ShipmentStatus
from app.models.production import ProductionOrder, OPMaterial, OPStatus

router = APIRouter(prefix="/production", tags=["Production"])
templates = Jinja2Templates(directory="app/templates")

@router.post("/register")
async def register_production(
    worker_id: int = Form(...),
    product_id: int = Form(...),
    quantity: float = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(login_required)
):
    # 1. Validate Worker and Product
    worker = db.query(Worker).filter(Worker.id == worker_id, Worker.company_id == user.company_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Terceirizado não encontrado")
        
    product = db.query(Product).filter(Product.id == product_id, Product.company_id == user.company_id).first()
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

    components = db.query(ProductComposition).join(Product, ProductComposition.composite_id == Product.id).filter(
        ProductComposition.composite_id == product_id,
        Product.company_id == user.company_id
    ).all()
    
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
            (Shipment.quantity - Shipment.returned_quantity) > 0, # Has balance
            Shipment.company_id == user.company_id
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
        company_id=user.company_id,
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


# --- OP Routes ---

@router.get("/orders")
async def list_production_orders(request: Request, db: Session = Depends(get_db), user: User = Depends(login_required)):
    ops = db.query(ProductionOrder).filter(ProductionOrder.company_id == user.company_id).order_by(ProductionOrder.created_at.desc()).all()
    # To create an OP, we need a list of composite products
    composite_products = db.query(Product).filter(Product.company_id == user.company_id, Product.is_composite == True).all()
    
    return templates.TemplateResponse("production_orders.html", {
        "request": request,
        "user": user,
        "ops": ops,
        "composite_products": composite_products,
        "OPStatus": OPStatus
    })

@router.post("/orders/new")
async def create_production_order(
    product_id: int = Form(...),
    expected_quantity: float = Form(...),
    notes: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(login_required)
):
    if expected_quantity <= 0:
         raise HTTPException(status_code=400, detail="A quantidade esperada deve ser maior que zero.")
    
    product = db.query(Product).filter(Product.id == product_id, Product.company_id == user.company_id).first()
    if not product or not product.is_composite:
         raise HTTPException(status_code=400, detail="Produto inválido para uma OP (Deve ser composto).")
         
    # Generate OP Number OP-YYYYMMDD-XXXX
    today_str = datetime.now().strftime("%Y%m%d")
    count_today = db.query(ProductionOrder).filter(
        ProductionOrder.company_id == user.company_id,
        ProductionOrder.op_number.like(f"OP-{today_str}-%")
    ).count()
    op_num = f"OP-{today_str}-{count_today + 1:04d}"
    
    new_op = ProductionOrder(
        op_number=op_num,
        company_id=user.company_id,
        product_id=product.id,
        expected_quantity=expected_quantity,
        status=OPStatus.DRAFT,
        notes=notes
    )
    db.add(new_op)
    db.flush() # get new_op.id
    
    # Generate needed materials
    compositions = db.query(ProductComposition).filter(ProductComposition.composite_id == product.id).all()
    for comp in compositions:
        total_needed = expected_quantity * comp.quantity
        op_mat = OPMaterial(
            op_id=new_op.id,
            component_id=comp.component_id,
            expected_quantity=total_needed,
            company_id=user.company_id
        )
        db.add(op_mat)
        
    db.commit()
    return RedirectResponse(url="/production/orders", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/orders/{op_id}/details")
async def view_production_order(op_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(login_required)):
    op = db.query(ProductionOrder).filter(ProductionOrder.id == op_id, ProductionOrder.company_id == user.company_id).first()
    if not op:
         raise HTTPException(status_code=404, detail="OP não encontrada")
         
    return templates.TemplateResponse("production_order_view.html", {
        "request": request,
        "user": user,
        "op": op,
        "OPStatus": OPStatus
    })
