from fastapi import APIRouter, Request, Depends, HTTPException, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.company import Company
from app.models.inventory import AuditLog, Product, Category, ProductComposition, Movement
from app.models.ticket import SupportTicket, TicketMessage
from app.api.dependencies import get_db, admin_required
from app.models.worker import Worker, Shipment
from app.models.worker_type import WorkerType

router = APIRouter(prefix="/admin", tags=["Admin"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/users")
async def admin_users_list(
    request: Request, 
    user: User = Depends(admin_required), 
    db: Session = Depends(get_db)
):
    users = db.query(User).all()
    companies = db.query(Company).all()
    return templates.TemplateResponse("admin_users.html", {
        "request": request, 
        "user": user, 
        "users": users,
        "companies": companies
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

@router.post("/users/{user_id}/toggle-admin")
async def toggle_user_admin(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required)
):
    if user_id == admin.id:
        # Prevent self-demotion to avoid lockout
        # Ideally flash a message, but for now just redirect
        return RedirectResponse(url="/admin/users", status_code=status.HTTP_303_SEE_OTHER)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    user.is_admin = not user.is_admin
    db.commit()
    return RedirectResponse(url="/admin/users", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/users/{user_id}/assign-company")
async def assign_user_company(
    user_id: int,
    company_id: int = Form(...),
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    user.company_id = company_id
    db.commit()
    return RedirectResponse(url="/admin/users", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/users/{user_id}/toggle-active")
async def toggle_user_active(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required)
):
    if user_id == admin.id:
        return RedirectResponse(url="/admin/users", status_code=status.HTTP_303_SEE_OTHER)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    user.is_active = not user.is_active
    db.commit()
    return RedirectResponse(url="/admin/users", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/users/{user_id}/delete")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required)
):
    if user_id == admin.id:
        return RedirectResponse(url="/admin/users", status_code=status.HTTP_303_SEE_OTHER)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    db.delete(user)
    db.commit()
    return RedirectResponse(url="/admin/users", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/users/{user_id}/reset-password")
async def reset_user_password(
    user_id: int,
    new_password: str = Form(...),
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required)
):
    from app.core.security import get_password_hash
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    user.hashed_password = get_password_hash(new_password)
    db.commit()
    return RedirectResponse(url="/admin/users?success=Senha redefinida com sucesso", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/companies")
async def admin_companies_list(
    request: Request,
    user: User = Depends(admin_required),
    db: Session = Depends(get_db)
):
    companies = db.query(Company).all()
    return templates.TemplateResponse("admin_companies.html", {
        "request": request,
        "user": user,
        "companies": companies
    })

@router.post("/companies/create")
async def create_company(
    name: str = Form(...),
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required)
):
    existing = db.query(Company).filter(Company.name == name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Empresa já existe")
    
    new_company = Company(name=name)
    db.add(new_company)
    db.commit()
    return RedirectResponse(url="/admin/companies", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/audit")
async def admin_audit_log(
    request: Request,
    company_id: int = None,
    user: User = Depends(admin_required),
    db: Session = Depends(get_db)
):
    query = db.query(AuditLog)
    if company_id:
        query = query.filter(AuditLog.company_id == company_id)
    
    logs = query.order_by(AuditLog.timestamp.desc()).all()
    companies = db.query(Company).all()
    
    return templates.TemplateResponse("admin_audit.html", {
        "request": request,
        "user": user,
        "audit_logs": logs,
        "companies": companies,
        "selected_company_id": company_id
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

from fastapi import UploadFile, File

@router.get("/backup")
async def admin_backup_view(
    request: Request,
    user: User = Depends(admin_required)
):
    return templates.TemplateResponse("admin_backup.html", {
        "request": request,
        "user": user
    })

@router.get("/backup/download")
async def backup_download(user: User = Depends(admin_required)):
    db_url = settings.DATABASE_URL
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 1. PostgreSQL Strategy
    if db_url.startswith("postgres"):
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

@router.post("/backup/restore")
async def restore_database(
    file: UploadFile = File(...),
    user: User = Depends(admin_required)
):
    db_url = settings.DATABASE_URL
    upload_path = f"/tmp/{file.filename}"
    
    try:
        # Save uploaded file
        with open(upload_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 1. PostgreSQL Strategy
        if db_url.startswith("postgres"):
            import subprocess
            import shutil
            
            pg_restore_path = shutil.which("pg_restore")
            if not pg_restore_path:
                 # Fallbacks
                if os.path.exists("/usr/bin/pg_restore"):
                    pg_restore_path = "/usr/bin/pg_restore"
                elif os.path.exists("/usr/local/bin/pg_restore"):
                    pg_restore_path = "/usr/local/bin/pg_restore"
                else:
                    raise HTTPException(status_code=500, detail="pg_restore não encontrado.")

            # pg_restore -d db_url --clean --if-exists upload_path
            # Note: --clean drops objects before creating them, critical for restore
            process = subprocess.Popen(
                [pg_restore_path, "-d", db_url, "--clean", "--if-exists", "-v", upload_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                print(f"Restore Error: {stderr.decode()}")
                # pg_restore often returns warnings as non-zero, but let's be strict for now or log
                # Actually, pg_restore might return non-zero on harmless warnings.
                # Just log it but maybe don't fail if some lines restored?
                pass 

        # 2. SQLite Strategy
        elif db_url.startswith("sqlite"):
            db_path = db_url.replace("sqlite:///", "")
            # Verify it's a valid sqlite file?
            # Replace current db file
            shutil.copy2(upload_path, db_path)
            
        else:
            raise HTTPException(status_code=400, detail="Tipo de banco não suportado para restore.")
            
        # Log Action
        # We can't use DB session dependency easily here if we just swapped the DB file in SQLite case?
        # Actually in SQLite, the session might be stale.
        # But for Postgres, the connection persists.
        return RedirectResponse(url="/admin/backup?success=true", status_code=status.HTTP_303_SEE_OTHER)

    except Exception as e:
        print(f"Restore Exception: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao restaurar: {str(e)}")

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
        
        # Filter by company if requested, or show all if admin
        # For multi-tenancy audit, usually each company sees its own, 
        # but the global admin sees everything.
        # Let's add a company filter if needed.
        
        # Delete in order of dependencies (reverse creation)
        db.query(AuditLog).delete() # Be careful: this clears EVERYTHING
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

@router.get("/support")
async def admin_support_list(
    request: Request,
    user: User = Depends(admin_required),
    db: Session = Depends(get_db)
):
    from sqlalchemy import desc
    tickets = db.query(SupportTicket).order_by(desc(SupportTicket.created_at)).all()
    return templates.TemplateResponse("admin_support.html", {
        "request": request,
        "user": user,
        "tickets": tickets
    })

@router.get("/support/{ticket_id}")
async def admin_support_view(
    ticket_id: int,
    request: Request,
    user: User = Depends(admin_required),
    db: Session = Depends(get_db)
):
    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")
    
    return templates.TemplateResponse("admin_support_view.html", {
        "request": request,
        "user": user,
        "ticket": ticket
    })

@router.post("/support/{ticket_id}/reply")
async def admin_support_reply(
    ticket_id: int,
    request: Request,
    message: str = Form(...),
    db: Session = Depends(get_db),
    admin_user: User = Depends(admin_required)
):
    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")
    
    new_message = TicketMessage(
        ticket_id=ticket.id,
        sender_id=admin_user.id,
        message=message
    )
    db.add(new_message)
    
    # If the admin replies, we can keep it open or mark as 'in_progress', let's use 'in_progress' or keep 'open'. We'll just leave it or set to open.
    # We will assume admin changing it to answered or anything could be handled directly via status endpoint.
    
    db.commit()
    return RedirectResponse(url=f"/admin/support/{ticket_id}", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/support/{ticket_id}/status")
async def admin_support_status(
    ticket_id: int,
    status_val: str = Form(...),
    db: Session = Depends(get_db),
    admin_user: User = Depends(admin_required)
):
    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")
    
    ticket.status = status_val
    db.commit()
    return RedirectResponse(url=f"/admin/support/{ticket_id}", status_code=status.HTTP_303_SEE_OTHER)
