import io
import csv
import uuid
from fastapi import APIRouter, Request, Depends, HTTPException, status, Form, UploadFile, File
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import json
from app.models.inventory import Product, Category, Movement, AuditLog, ProductComposition

from app.models.user import User
from app.api.dependencies import get_db, login_required

router = APIRouter(prefix="/inventory", tags=["Inventory"])
templates = Jinja2Templates(directory="app/templates")

@router.get("")
@router.get("/")
async def inventory_view(request: Request, user: User = Depends(login_required), db: Session = Depends(get_db)):
    products = db.query(Product).filter(Product.company_id == user.company_id).all()
    categories = db.query(Category).filter(Category.company_id == user.company_id).all()
    return templates.TemplateResponse("inventory.html", {
        "request": request, 
        "user": user, 
        "products": products,
        "categories": categories
    })

@router.post("/products")
async def create_product(
    name: str = Form(...),
    description: str = Form(None),
    category_id: int = Form(...),
    unit: str = Form("Und"),
    is_composite: bool = Form(False),
    is_primary: bool = Form(False),
    sku: str = Form(None),
    composition_data: str = Form(None), # JSON string

    db: Session = Depends(get_db),
    user: User = Depends(login_required)
):
    if not sku:
        sku = f"PROD-{uuid.uuid4().hex[:8].upper()}"

    new_product = Product(
        sku=sku,
        name=name,
        description=description,
        category_id=category_id,
        unit=unit,
        is_composite=is_composite,
        is_primary=is_primary,
        current_stock=0.0,
        company_id=user.company_id
    )
    db.add(new_product)
    db.flush()
    
    # Process Composition
    if is_composite and composition_data:
        try:
            items = json.loads(composition_data)
            for item in items:
                comp = ProductComposition(
                    composite_id=new_product.id,
                    component_id=int(item['id']),
                    quantity=float(item['quantity']),
                    company_id=user.company_id
                )
                db.add(comp)
        except Exception as e:
            print(f"Error processing composition: {e}")
            # Optionally raise HTTPException, but for now just log
    
    db.add(AuditLog(
        user_id=user.id,
        company_id=user.company_id,
        action="CREATE_PRODUCT",
        resource_type="product",
        resource_id=new_product.id,
        description=f"Produto '{name}' (Unidade: {unit}) criado. Classificação: {'Composto' if is_composite else ''} {'Primário' if is_primary else ''}"
    ))
    
    db.commit()
    return RedirectResponse(url="/inventory", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/products/{product_id}/update")
async def update_product(
    product_id: int,
    name: str = Form(...),
    description: str = Form(None),
    category_id: int = Form(...),
    unit: str = Form("Und"),
    is_composite: bool = Form(False),
    is_primary: bool = Form(False),
    composition_data: str = Form(None), # JSON string
    db: Session = Depends(get_db),
    user: User = Depends(login_required)
):
    product = db.query(Product).filter(Product.id == product_id, Product.company_id == user.company_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    
    product.name = name
    product.description = description
    product.category_id = category_id
    product.unit = unit
    product.is_composite = is_composite
    product.is_primary = is_primary
    
    # Process Composition Update
    if is_composite:
        # Simple strategy: Delete all and recreate
        try:
            db.query(ProductComposition).filter(
                ProductComposition.composite_id == product.id,
                ProductComposition.company_id == user.company_id
            ).delete()
            if composition_data:
                items = json.loads(composition_data)
                for item in items:
                    comp = ProductComposition(
                        composite_id=product.id,
                        component_id=int(item['id']),
                        quantity=float(item['quantity']),
                        company_id=user.company_id
                    )
                    db.add(comp)
        except Exception as e:
             print(f"Error updating composition: {e}")
    else:
        # If not composite anymore, cleanup
        db.query(ProductComposition).filter(
            ProductComposition.composite_id == product.id,
            ProductComposition.company_id == user.company_id
        ).delete()

    
    db.add(AuditLog(
        user_id=user.id,
        company_id=user.company_id,
        action="UPDATE_PRODUCT",
        resource_type="product",
        resource_id=product.id,
        description=f"Produto '{name}' atualizado."
    ))
    db.commit()
    return RedirectResponse(url="/inventory", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/products/{product_id}/delete")
async def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(login_required)
):
    product = db.query(Product).filter(Product.id == product_id, Product.company_id == user.company_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    
    # Check Verification
    # 1. Movements
    mov_count = db.query(Movement).filter(Movement.product_id == product_id, Movement.company_id == user.company_id).count()
    if mov_count > 0:
        raise HTTPException(status_code=400, detail=f"Não é possível excluir: existem {mov_count} movimentações registradas.")
    
    # 2. Shipments
    from app.models.worker import Shipment
    ship_count = db.query(Shipment).filter(Shipment.product_id == product_id, Shipment.company_id == user.company_id).count()
    if ship_count > 0:
        raise HTTPException(status_code=400, detail=f"Não é possível excluir: existem {ship_count} remessas para terceirizados.")

    db.add(AuditLog(
        user_id=user.id,
        company_id=user.company_id,
        action="DELETE_PRODUCT",
        resource_type="product",
        resource_id=product_id,
        description=f"Produto '{product.name}' excluído."
    ))
    db.delete(product)
    db.commit()
    return RedirectResponse(url="/inventory", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/export")
async def export_inventory(
    db: Session = Depends(get_db),
    user: User = Depends(login_required)
):
    products = db.query(Product).filter(Product.company_id == user.company_id).all()
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        "sku", "name", "description", "category", "current_stock", "unit"
    ])
    writer.writeheader()
    for p in products:
        writer.writerow({
            "sku": p.sku,
            "name": p.name,
            "description": p.description or "",
            "category": p.category.name if p.category else "",
            "current_stock": p.current_stock,
            "unit": p.unit or "un"
        })
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=estoque_invexa.csv"}
    )

@router.post("/import")
async def import_inventory(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(login_required)
):
    content = await file.read()
    decoded = content.decode("utf-8-sig").splitlines()
    reader = csv.DictReader(decoded)
    for row in reader:
        sku = row.get("sku")
        
        # If SKU provided, check existence. If not, generated later for new products.
        product = None
        if sku:
            product = db.query(Product).filter(Product.sku == sku, Product.company_id == user.company_id).first()
            
        cat_name = row.get("category")
        category_id = None
        if cat_name:
            cat = db.query(Category).filter(Category.name == cat_name, Category.company_id == user.company_id).first()
            if not cat:
                cat = Category(name=cat_name, company_id=user.company_id)
                db.add(cat)
                db.flush()
            category_id = cat.id
            
        if product:
            product.name = row.get("name", product.name)
            product.description = row.get("description", product.description)
            product.category_id = category_id or product.category_id
            if row.get("current_stock"):
                product.current_stock = float(row.get("current_stock"))
            product.unit = row.get("unit", product.unit)
        else:
            if not sku:
                sku = f"PROD-{uuid.uuid4().hex[:8].upper()}"
            
            new_product = Product(
                sku=sku,
                name=row.get("name", "Novo Produto"),
                description=row.get("description", ""),
                category_id=category_id,
                current_stock=float(row.get("current_stock", 0)),
                unit=row.get("unit", "un"),
                company_id=user.company_id
            )
            db.add(new_product)
    db.commit()
    return RedirectResponse(url="/inventory", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/categories")
@router.get("/categories/")
async def categories_view(request: Request, user: User = Depends(login_required), db: Session = Depends(get_db)):
    categories = db.query(Category).filter(Category.company_id == user.company_id).all()
    return RedirectResponse(url="/inventory?tab=categories", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/categories")
@router.post("/categories/")
async def create_category(
    name: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(login_required)
):
    existing = db.query(Category).filter(Category.name == name, Category.company_id == user.company_id).first()
    if not existing:
        new_cat = Category(name=name, company_id=user.company_id)
        db.add(new_cat)
        db.flush()
        db.add(AuditLog(
            user_id=user.id,
            company_id=user.company_id,
            action="CREATE_CATEGORY",
            resource_type="category",
            resource_id=new_cat.id,
            description=f"Categoria '{name}' criada."
        ))
        db.commit()
    return RedirectResponse(url="/inventory?tab=categories", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/categories/{category_id}/delete")
async def delete_category(
    request: Request,
    category_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(login_required)
):
    category = db.query(Category).filter(Category.id == category_id, Category.company_id == user.company_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    product_count = db.query(Product).filter(Product.category_id == category_id, Product.company_id == user.company_id).count()
    if product_count > 0:
        categories = db.query(Category).filter(Category.company_id == user.company_id).all()
        # Redirect with error query param to be displayed by frontend
        # Alternatively, could render inventory.html with error, but redirection is simpler for now
        # We'll use a session cookie or query param. Query param is easiest:
        return RedirectResponse(
            url=f"/inventory?tab=categories&error=Não é possível excluir: existem {product_count} produtos vinculados a esta categoria.", 
            status_code=status.HTTP_303_SEE_OTHER
        )
    db.add(AuditLog(
        user_id=user.id,
        company_id=user.company_id,
        action="DELETE_CATEGORY",
        resource_type="category",
        resource_id=category_id,
        description=f"Categoria '{category.name}' (ID: {category_id}) excluída."
    ))
    db.delete(category)
    db.commit()
    return RedirectResponse(url="/inventory?tab=categories", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/products/{product_id}")
async def get_product_details(
    product_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(login_required)
):
    product = db.query(Product).filter(Product.id == product_id, Product.company_id == user.company_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
        
    history = db.query(Movement).filter(Movement.product_id == product_id, Movement.company_id == user.company_id).order_by(Movement.timestamp.desc()).limit(10).all()
    
    # Fetch Composition
    composition = db.query(ProductComposition).filter(
        ProductComposition.composite_id == product_id,
        ProductComposition.company_id == user.company_id
    ).all()
    comp_list = []
    for c in composition:
        comp_list.append({
            "id": c.component.id,
            "name": c.component.name,
            "quantity": c.quantity,
            "unit": c.component.unit
        })

    return {
        "id": product.id,
        "sku": product.sku,
        "name": product.name,
        "description": product.description,
        "category": product.category.name if product.category else "-",
        "unit": product.unit or "un",
        "current_stock": product.current_stock,
        "is_composite": product.is_composite,
        "is_primary": product.is_primary,
        "composition": comp_list,
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
