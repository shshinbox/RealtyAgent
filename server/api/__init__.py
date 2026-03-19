from fastapi import APIRouter

from .auth import router as auth_router
from .inference import router as inference_router
from .documents import router as documents_router
from .pages import router as pages_router


api_router = APIRouter()


api_router.include_router(router=auth_router)
api_router.include_router(prefix="/chat", router=inference_router)
api_router.include_router(prefix="/documents", router=documents_router)
api_router.include_router(router=pages_router)
