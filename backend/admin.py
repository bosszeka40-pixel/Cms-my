from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr
from .cms_core import CMSEngine

router = APIRouter(prefix="/api/admin", tags=["admin"])
engine = CMSEngine()

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class PluginCreate(BaseModel):
    name: str
    price: float
    description: str = ""


def _normalize_email(email: str) -> str:
    return email.strip().lower()


@router.post("/users")
def create_user(payload: UserCreate, request: Request):
    _require_admin(request)
    email = _normalize_email(payload.email)
    existing = engine.get_user(email)
    if existing:
        raise HTTPException(status_code=400, detail="Пользователь уже существует")
    user = engine.create_user(email, payload.password)
    return {"id": user.id, "email": user.email, "kyc_status": user.kyc_status}


@router.post("/login")
def admin_login(payload: UserLogin, request: Request):
    email = _normalize_email(payload.email)
    user = engine.secure_login(email, payload.password)
    if not user or user.role != "admin":
        raise HTTPException(status_code=401, detail="Неверный email или пароль администратора")
    request.session["user_email"] = user.email
    request.session["is_admin"] = True
    return {"status": "success", "email": user.email, "role": user.role}


@router.post("/plugins")
def create_plugin(payload: PluginCreate, request: Request):
    _require_admin(request)
    if payload.price < 0:
        raise HTTPException(status_code=400, detail="Цена не может быть отрицательной")
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Название плагина не может быть пустым")
    plugin = engine.create_plugin(name, payload.price, payload.description.strip())
    return {"id": plugin.id, "name": plugin.name, "price": plugin.price}


@router.get("/plugins")
def list_plugins(request: Request):
    _require_admin(request)
    return [{"id": plugin.id, "name": plugin.name, "price": plugin.price, "description": plugin.description} for plugin in engine.list_plugins()]


def _require_admin(request: Request):
    email = request.session.get("user_email")
    user = engine.get_user(email) if email else None
    if not user or user.role != "admin":
        raise HTTPException(status_code=403, detail="Требуются права администратора.")
    return user
