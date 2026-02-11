from fastapi import Request, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core import database, security
from app.models.user import User

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_current_user_from_cookie(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        return None
    
    payload = security.decode_access_token(token)
    if not payload:
        return None
    
    email = payload.get("sub")
    if not email:
        return None
        
    user = db.query(User).filter(User.email == email).first()
    return user

def login_required(user: User = Depends(get_current_user_from_cookie)):
    if not user:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/login"}
        )
    return user

def admin_required(user: User = Depends(login_required)):
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a administradores"
        )
    return user
