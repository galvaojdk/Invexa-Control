import xml.etree.ElementTree as ET
from fastapi import APIRouter, Request, Depends, HTTPException, Form, UploadFile, File, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.models.inventory import Product, Category, Reception, ReceptionItem, ReceptionStatus, MovementType
from app.models.user import User
from app.api.dependencies import get_db, login_required
from app.services.inventory_service import InventoryService

router = APIRouter(prefix="/receptions", tags=["Receptions"])
templates = Jinja2Templates(directory="app/templates")

@router.get("")
@router.get("/")
async def receptions_list(request: Request, user: User = Depends(login_required), db: Session = Depends(get_db)):
    receptions = db.query(Reception).order_by(Reception.created_at.desc()).all()
    products = db.query(Product).all()
    return templates.TemplateResponse("receptions.html", {
        "request": request,
        "user": user,
        "receptions": receptions,
        "products": products
    })

@router.post("")
@router.post("/")
async def create_reception(
    document_number: str = Form(...),
    supplier_name: str = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(login_required)
):
    new_reception = Reception(
        document_number=document_number,
        supplier_name=supplier_name,
        user_id=user.id,
        status=ReceptionStatus.PENDING
    )
    db.add(new_reception)
    db.commit()
    return RedirectResponse(url=f"/receptions/{new_reception.id}", status_code=303)

@router.post("/import-xml")
async def import_reception_xml(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(login_required)
):
    try:
        content = await file.read()
        root = ET.fromstring(content)
        ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
        inf_nfe = root.find('.//nfe:infNFe', ns)
        if inf_nfe is None:
            inf_nfe = root.find('.//infNFe')
            if inf_nfe is None: raise ValueError("XML de NFe inválido")
            ns = {}
        ide = inf_nfe.find('nfe:ide', ns) if ns else inf_nfe.find('ide')
        nnf = ide.find('nfe:nNF', ns).text if ns else ide.find('nNF').text
        emit = inf_nfe.find('nfe:emit', ns) if ns else inf_nfe.find('emit')
        supplier = emit.find('nfe:xNome', ns).text if ns else emit.find('xNome').text
        
        new_reception = Reception(
            document_number=f"NF-{nnf}",
            supplier_name=supplier,
            user_id=user.id,
            status=ReceptionStatus.PENDING
        )
        db.add(new_reception)
        db.flush()
        
        items = inf_nfe.findall('nfe:det', ns) if ns else inf_nfe.findall('det')
        for det in items:
            prod_tag = det.find('nfe:prod', ns) if ns else det.find('prod')
            cprod = prod_tag.find('nfe:cProd', ns).text
            xprod = prod_tag.find('nfe:xProd', ns).text
            qcom = float(prod_tag.find('nfe:qCom', ns).text)
            ucom = prod_tag.find('nfe:uCom', ns).text
            
            product = db.query(Product).filter(Product.sku == cprod).first()
            if not product:
                cat = db.query(Category).first()
                product = Product(name=xprod, sku=cprod, unit=ucom, category_id=cat.id if cat else 1)
                db.add(product)
                db.flush()
            
            db.add(ReceptionItem(reception_id=new_reception.id, product_id=product.id, expected_quantity=qcom))
            
        db.commit()
        return RedirectResponse(url=f"/receptions/{new_reception.id}", status_code=303)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Erro ao processar XML: {str(e)}")

@router.get("/{reception_id}")
async def reception_detail(reception_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(login_required)):
    reception = db.query(Reception).filter(Reception.id == reception_id).first()
    if not reception: raise HTTPException(status_code=404, detail="Não encontrado")
    products = db.query(Product).order_by(Product.name.asc()).all()
    return templates.TemplateResponse("reception_detail.html", {"request": request, "user": user, "reception": reception, "products": products})

@router.post("/{reception_id}/items")
async def add_reception_item(reception_id: int, product_id: int = Form(...), expected_quantity: float = Form(...), db: Session = Depends(get_db), user: User = Depends(login_required)):
    db.add(ReceptionItem(reception_id=reception_id, product_id=product_id, expected_quantity=expected_quantity))
    db.commit()
    return RedirectResponse(url=f"/receptions/{reception_id}", status_code=303)

@router.get("/{reception_id}/check")
async def reception_check_view(reception_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(login_required)):
    reception = db.query(Reception).filter(Reception.id == reception_id).first()
    if not reception: raise HTTPException(status_code=404, detail="Não encontrado")
    reception.status = ReceptionStatus.IN_PROGRESS
    db.commit()
    return templates.TemplateResponse("reception_check.html", {"request": request, "user": user, "reception": reception})

@router.post("/{reception_id}/finalize")
async def finalize_reception(reception_id: int, db: Session = Depends(get_db), user: User = Depends(login_required)):
    reception = db.query(Reception).filter(Reception.id == reception_id).first()
    if not reception or reception.status == ReceptionStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Inválido")
    
    # Injection into stock using InventoryService!
    for item in reception.items:
        if item.actual_quantity > 0:
            InventoryService.register_stock_movement(
                db=db,
                product_id=item.product_id,
                quantity=item.actual_quantity,
                mov_type=MovementType.IN,
                user_id=user.id,
                reason=f"Recebimento NF: {reception.document_number}",
                sector="Estoque Central"
            )
    
    reception.status = ReceptionStatus.COMPLETED
    db.commit()
    return RedirectResponse(url="/receptions", status_code=303)
