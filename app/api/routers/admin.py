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

from fastapi.responses import FileResponse
import shutil
import os
from datetime import datetime
from app.core.config import settings

@router.get("/backup")
async def backup_database(user: User = Depends(admin_required)):
    # Verify it is sqlite
    db_url = settings.DATABASE_URL
    if not db_url.startswith("sqlite"):
        raise HTTPException(status_code=400, detail="Backup automatico disponivel apenas para SQLite local.")
    
    # Extract file path: sqlite:///./control.db -> ./control.db
    # Remove sqlite:/// prefix
    db_path = db_url.replace("sqlite:///", "")
    
    if not os.path.exists(db_path):
         raise HTTPException(status_code=404, detail="Arquivo de banco de dados nao encontrado.")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"backup_invexa_{timestamp}.db"
    
    # Ensure backups dir exists
    backup_dir = "./backups"
    os.makedirs(backup_dir, exist_ok=True)
    
    backup_path = os.path.join(backup_dir, backup_filename)
    
    # Copy file (using copy2 to preserve metadata)
    shutil.copy2(db_path, backup_path)
    
    return FileResponse(path=backup_path, filename=backup_filename, media_type='application/octet-stream')
