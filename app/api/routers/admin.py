from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.inventory import AuditLog
from app.api.dependencies import get_db, admin_required

router = APIRouter(prefix="/admin", tags=["Admin"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/users")
async def admin_users_list(
    request: Request, 
    user: User = Depends(admin_required), 
    db: Session = Depends(get_db)
):
    users = db.query(User).all()
    return templates.TemplateResponse("admin_users.html", {
        "request": request, 
        "user": user, 
        "users": users
    })

@router.post("/users/{user_id}/toggle-premium")
async def toggle_user_premium(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    user.is_premium = not user.is_premium
    user.subscription_status = "active" if user.is_premium else "canceled"
    user.subscription_plan = "Premium Admin" if user.is_premium else None
    db.commit()
    return RedirectResponse(url="/admin/users", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/audit")
async def admin_audit_log(
    request: Request,
    user: User = Depends(admin_required),
    db: Session = Depends(get_db)
):
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).all()
    return templates.TemplateResponse("admin_audit.html", {
        "request": request,
        "user": user,
        "logs": logs
    })
