from fastapi import APIRouter
from .market_history import ensure_table

router = APIRouter(tags=['system'])

@router.get('/health')
def health():
    return {'status': 'ok'}

@router.get('/ready')
def ready():
    ensure_table()
    return {'status': 'ready'}
