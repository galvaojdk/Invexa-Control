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
        "audit_logs": logs
    })

@router.post("/audit/clear")
async def clear_audit_logs(
    db: Session = Depends(get_db),
    user: User = Depends(admin_required)
):
    try:
        # Delete all records
        db.query(AuditLog).delete()
        db.commit()
        return RedirectResponse(url="/admin/audit", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao limpar logs: {str(e)}")

from fastapi.responses import FileResponse
import shutil
import os
from datetime import datetime
from app.core.config import settings

@router.get("/backup")
async def backup_database(user: User = Depends(admin_required)):
    db_url = settings.DATABASE_URL
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 1. PostgreSQL Strategy
    if db_url.startswith("postgres"):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_invexa_pg_{timestamp}.dump"
        backup_path = os.path.join("/tmp", backup_filename)
        
        try:
            import subprocess
            import shutil
            
            # Locate pg_dump explicitly
            pg_dump_path = shutil.which("pg_dump")
            if not pg_dump_path:
                print("BACKUP ERROR: pg_dump not found in PATH.")
                print(f"Current PATH: {os.environ.get('PATH')}")
                if os.path.exists("/usr/bin/pg_dump"):
                    pg_dump_path = "/usr/bin/pg_dump"
                elif os.path.exists("/usr/local/bin/pg_dump"):
                    pg_dump_path = "/usr/local/bin/pg_dump"
                else:
                    raise HTTPException(status_code=500, detail="Ferramenta pg_dump não encontrada no servidor.")
            
            print(f"Using pg_dump at: {pg_dump_path}")

            process = subprocess.Popen(
                [pg_dump_path, "-d", db_url, "-F", "c", "-b", "-v", "-f", backup_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                print(f"Backup Error: {stderr.decode()}")
                raise HTTPException(status_code=500, detail="Erro ao gerar backup do PostgreSQL.")
                
            return FileResponse(path=backup_path, filename=backup_filename, media_type='application/octet-stream')
            
        except HTTPException as he:
            raise he
        except Exception as e:
            print(f"Backup Exception: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Erro interno de backup: {str(e)}")

@router.get("/reset")
async def admin_reset_view(
    request: Request,
    user: User = Depends(admin_required)
):
    return templates.TemplateResponse("admin_reset.html", {
        "request": request,
        "user": user
    })

@router.post("/reset")
async def admin_reset_database(
    db: Session = Depends(get_db),
    user: User = Depends(admin_required)
):
    try:
        from app.models.inventory import Product, Category, ProductComposition, Movement, AuditLog
        from app.models.worker import Worker, Shipment
        from app.models.worker_type import WorkerType
        
        # Delete in order of dependencies (reverse creation)
        db.query(AuditLog).delete()
        db.query(Movement).delete()
        db.query(Shipment).delete()
        db.query(ProductComposition).delete()
        db.query(Product).delete()
        db.query(Worker).delete()
        db.query(WorkerType).delete()
        db.query(Category).delete()
        
        # Log the reset action (Wait, we just deleted logs... create a new one)
        db.add(AuditLog(
            user_id=user.id,
            action="SYSTEM_RESET",
            resource_type="system",
            resource_id=0,
            description="Sistema resetado pelo administrador (Dados apagados)."
        ))
        
        db.commit()
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao resetar banco: {str(e)}")

    # 2. SQLite Strategy (Local Development)
    elif db_url.startswith("sqlite"):
        db_path = db_url.replace("sqlite:///", "")
        if not os.path.exists(db_path):
             raise HTTPException(status_code=404, detail="Arquivo de banco de dados nao encontrado.")

        backup_filename = f"backup_invexa_sqlite_{timestamp}.db"
        # Use simple temp dir for backups to avoid permission issues on some hostings
        backup_dir = "./backups" 
        os.makedirs(backup_dir, exist_ok=True)
        backup_path = os.path.join(backup_dir, backup_filename)
        
        shutil.copy2(db_path, backup_path)
        return FileResponse(path=backup_path, filename=backup_filename, media_type='application/octet-stream')

    else:
        raise HTTPException(status_code=400, detail="Tipo de banco de dados nao suportado para backup automatico.")
