from functools import partial
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse
import uuid
from typing import AsyncGenerator
from wrapt import partial

from engine import GraphEngine

from server.storage.operations import (
    enqueue_memory_task,
    get_user_persona,
)
from ..auth import get_current_user_id


router = APIRouter()


@router.post("/chat")
async def new(
    request: Request, user_query: str, user_id: str = Depends(get_current_user_id)
) -> StreamingResponse:
    thread_id: str = str(uuid.uuid4())

    engine: GraphEngine = request.app.state.engine

    generator: AsyncGenerator = engine.run(
        query=user_query,
        thread_id=thread_id,
        user_id=user_id,
        external_fns=_external_deps(request),
    )
    return StreamingResponse(generator, media_type="text/event-stream")


@router.post("/chat/{thread_id}")
async def run(
    request: Request,
    thread_id: str,
    user_query: str,
    user_id: str = Depends(get_current_user_id),
) -> StreamingResponse:
    engine: GraphEngine = request.app.state.engine
    generator: AsyncGenerator = engine.run(
        query=user_query,
        thread_id=thread_id,
        user_id=user_id,
        external_fns=_external_deps(request),
    )
    return StreamingResponse(generator, media_type="text/event-stream")


@router.post("/chat/{thread_id}/resume")
async def resume(
    request: Request,
    thread_id: str,
    feedback: str,
    user_id: str = Depends(get_current_user_id),
) -> StreamingResponse:
    engine: GraphEngine = request.app.state.engine
    generator: AsyncGenerator = engine.resume(
        thread_id=thread_id,
        feedback=feedback,
        user_id=user_id,
        external_fns=_external_deps(request),
    )
    return StreamingResponse(generator, media_type="text/event-stream")


@router.get("/chat/{thread_id}/state")
async def state(
    request: Request, thread_id: str, user_id: str = Depends(get_current_user_id)
):
    engine: GraphEngine = request.app.state.engine
    state = await engine.aget_state(thread_id=thread_id, user_id=user_id)

    if state is None:
        raise HTTPException(status_code=404, detail="state not Found.")

    return state


def _external_deps(request: Request) -> dict:
    return {
        "search_memory_fn": partial(
            get_user_persona, db_engine=request.app.state.postgresql
        ),
        "push_task_fn": partial(
            enqueue_memory_task, redis_client=request.app.state.redis_client
        ),
    }
