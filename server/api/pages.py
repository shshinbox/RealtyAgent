from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter()


@router.get("/")
async def root():
    return FileResponse("frontend/index.html")


@router.get("/c/{thread_id}")
async def chat_room(thread_id: str):
    return FileResponse("frontend/index.html")
