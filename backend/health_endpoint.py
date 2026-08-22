from fastapi import APIRouter, Response

from .health_check import startup_health_check

router = APIRouter()


@router.get("/health")
def health(response: Response):
    result = startup_health_check()
    if result["status"] != "ready":
        response.status_code = 503
    return result
