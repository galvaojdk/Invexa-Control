from fastapi import APIRouter, Request, Depends, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.core import security, database
from app.models.user import User
from app.api.dependencies import get_db, login_required

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/login")
@router.get("/login/")
async def login_view(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login")
@router.post("/login/")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == email).first()
    if not user or not security.verify_password(password, user.hashed_password):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "E-mail ou senha incorretos"
        })
    
    access_token = security.create_access_token(data={"sub": user.email})
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="access_token", value=access_token, httponly=True)
    return response

@router.get("/register")
@router.get("/register/")
async def register_view(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@router.post("/register")
@router.post("/register/")
async def register(
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    db_user = db.query(User).filter(User.email == email).first()
    if db_user:
        return "Usuário já existe"
        
    hashed_password = security.get_password_hash(password)
    new_user = User(email=email, hashed_password=hashed_password, full_name=full_name)
    db.add(new_user)
    db.commit()
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/logout")
async def logout_view():
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("access_token")
    return response

@router.get("/profile")
async def profile_view(
    request: Request, 
    user: User = Depends(login_required),
    success: str = None,
    error: str = None
):
    return templates.TemplateResponse("profile.html", {
        "request": request, 
        "user": user,
        "success": success,
        "error": error
    })

@router.post("/profile/update")
async def profile_update(
    full_name: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(login_required)
):
    user.full_name = full_name
    db.commit()
    return RedirectResponse(url="/profile?success=Dados atualizados com sucesso", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/profile/password")
async def profile_password(
    new_password: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(login_required)
):
    user.hashed_password = security.get_password_hash(new_password)
    db.commit()
    return RedirectResponse(url="/profile?success=Senha alterada com sucesso", status_code=status.HTTP_303_SEE_OTHER)
