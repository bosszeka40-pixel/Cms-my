from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from .cms_core import CMSEngine

router = APIRouter(prefix="/api/admin", tags=["admin"])
engine = CMSEngine()

class UserCreate(BaseModel):
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class PluginCreate(BaseModel):
    name: str
    price: float
    description: str = ""

@router.post("/users")
def create_user(payload: UserCreate, request: Request):
    _require_admin(request)
    existing = engine.get_user(payload.email)
    if existing:
        raise HTTPException(status_code=400, detail="Пользователь уже существует")
    user = engine.create_user(payload.email, payload.password)
    return {"id": user.id, "email": user.email, "kyc_status": user.kyc_status}

@router.post("/login")
def admin_login(payload: UserLogin):
    user = engine.secure_login(payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Неверный email или пароль")
    return {"status": "success", "email": user.email, "role": user.role}

@router.post("/plugins")
def create_plugin(payload: PluginCreate, request: Request):
    _require_admin(request)
    plugin = engine.create_plugin(payload.name, payload.price, payload.description)
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
