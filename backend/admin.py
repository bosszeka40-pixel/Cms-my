from fastapi import APIRouter, HTTPException
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
def create_user(payload: UserCreate):
    existing = engine.get_user(payload.email)
    if existing:
        raise HTTPException(status_code=400, detail="Пользователь уже существует")
    user = engine.create_user(payload.email, payload.password)
    return {"id": user.id, "email": user.email, "kyc_status": user.kyc_status}

@router.post("/login")
def login(payload: UserLogin):
    user = engine.secure_login(payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Неверный email или пароль")
    return {"status": "success", "email": user.email, "role": user.role}

@router.post("/plugins")
def create_plugin(payload: PluginCreate):
    plugin = engine.create_plugin(payload.name, payload.price, payload.description)
    return {"id": plugin.id, "name": plugin.name, "price": plugin.price}

@router.get("/plugins")
def list_plugins():
    return [{"id": plugin.id, "name": plugin.name, "price": plugin.price, "description": plugin.description} for plugin in engine.list_plugins()]
