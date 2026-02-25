from fastapi import APIRouter, Depends, Form, Request, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.user import User
from app.models.system import SystemGuide
from app.api.dependencies import get_db, login_required

router = APIRouter(tags=["System Guide"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/api/guide/status")
async def get_guide_status(user: User = Depends(login_required), db: Session = Depends(get_db)):
    guide = db.query(SystemGuide).order_by(SystemGuide.id.desc()).first()
    if not guide:
        return JSONResponse({"version": 0, "has_update": False})
    
    # Check if user needs an update
    has_update = (guide.version > (user.guide_version_viewed or 0))
    return JSONResponse({"version": guide.version, "has_update": has_update})

@router.get("/api/guide/content")
async def get_guide_content(db: Session = Depends(get_db)):
    guide = db.query(SystemGuide).order_by(SystemGuide.id.desc()).first()
    if not guide:
        return {"content": "Nenhum guia disponível no momento.", "version": 0}
    
    return {"content": guide.content, "version": guide.version}

@router.post("/api/guide/mark_read")
async def mark_guide_read(user: User = Depends(login_required), db: Session = Depends(get_db)):
    guide = db.query(SystemGuide).order_by(SystemGuide.id.desc()).first()
    if guide and user:
        user.guide_version_viewed = guide.version
        db.commit()
    return {"status": "ok"}

@router.get("/admin/guide")
async def admin_edit_guide(request: Request, user: User = Depends(login_required), db: Session = Depends(get_db)):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Acesso Restrito")
    guide = db.query(SystemGuide).order_by(SystemGuide.id.desc()).first()
    if not guide: # Create placeholder if missing
        guide = SystemGuide(content="<p>Guia Vazio</p>", version=1)
        db.add(guide)
        db.commit()
        db.refresh(guide)
        
    return templates.TemplateResponse("admin_guide.html", {"request": request, "user": user, "guide": guide})

@router.post("/admin/guide")
async def admin_save_guide(content: str = Form(...), user: User = Depends(login_required), db: Session = Depends(get_db)):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Acesso Restrito")
        
    guide = db.query(SystemGuide).order_by(SystemGuide.id.desc()).first()
    if not guide:
        guide = SystemGuide()
        db.add(guide)
        
    guide.content = content
    guide.version += 1 # Upgrade format
    db.commit()
    
    return RedirectResponse(url="/admin/guide", status_code=303)
