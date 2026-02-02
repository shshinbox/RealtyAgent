from fastapi import APIRouter

from .inference import router as inference_router


api_router = APIRouter()


api_router.include_router(prefix="/chat", router=inference_router)
