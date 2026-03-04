from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse
from fastapi.responses import FileResponse
import uuid
from pathlib import Path

from engine import GraphEngine

from ..renderer.html_renderer import HtmlRenderer
from ..service.external_deps_service import ExternalDeps
from ..auth import get_current_user_id


router = APIRouter()


@router.post("/new")
async def new(
    request: Request, user_query: str, user_id: str = Depends(get_current_user_id)
) -> StreamingResponse:
    thread_id: str = str(uuid.uuid4())

    engine: GraphEngine = request.app.state.engine
    html_renderer = HtmlRenderer()

    async def stream_generator():
        async for chunk in engine.run(
            query=user_query,
            thread_id=thread_id,
            user_id=user_id,
            external_fns=_external_deps(request),
        ):
            result = html_renderer.format_event(chunk)
            if result:
                message, is_json = result
                html_chunk = await html_renderer.render_content(
                    message, is_json=is_json
                )
                yield f"data: {html_chunk}\n\n"

    return StreamingResponse(stream_generator(), media_type="text/event-stream")


@router.post("/{thread_id}")
async def run(
    request: Request,
    thread_id: str,
    user_query: str,
    user_id: str = Depends(get_current_user_id),
) -> StreamingResponse:
    engine: GraphEngine = request.app.state.engine
    html_renderer = HtmlRenderer()

    async def stream_generator():
        async for chunk in engine.run(
            query=user_query,
            thread_id=thread_id,
            user_id=user_id,
            external_fns=_external_deps(request),
        ):
            result = html_renderer.format_event(chunk)
            if result:
                message, is_json = result
                html_chunk = await html_renderer.render_content(
                    message, is_json=is_json
                )
                yield f"data: {html_chunk}\n\n"

    return StreamingResponse(stream_generator(), media_type="text/event-stream")


@router.post("/{thread_id}/resume")
async def resume(
    request: Request,
    thread_id: str,
    feedback: str,
    user_id: str = Depends(get_current_user_id),
) -> StreamingResponse:
    engine: GraphEngine = request.app.state.engine
    html_renderer = HtmlRenderer()

    async def stream_generator():
        async for chunk in engine.resume(
            thread_id=thread_id,
            feedback=feedback,
            user_id=user_id,
            external_fns=_external_deps(request),
        ):
            result = html_renderer.format_event(chunk)
            if result:
                message, is_json = result
                html_chunk = await html_renderer.render_content(
                    message, is_json=is_json
                )
                yield f"data: {html_chunk}\n\n"

    return StreamingResponse(stream_generator(), media_type="text/event-stream")


def _external_deps(request: Request):
    return ExternalDeps(request)


@router.get("/{thread_id}/state")
async def state(
    request: Request, thread_id: str, user_id: str = Depends(get_current_user_id)
):
    engine: GraphEngine = request.app.state.engine
    state = await engine.aget_state(thread_id=thread_id, user_id=user_id)

    if state is None:
        raise HTTPException(status_code=404, detail="state not Found.")

    return state


@router.get("/{thread_id}/download")
async def download_rendered_report(
    thread_id: str,
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    engine: GraphEngine = request.app.state.engine

    state = await engine.aget_state(thread_id=thread_id, user_id=user_id)
    final_answer = state.values.get("answer")
    if not final_answer:
        raise HTTPException(status_code=404, detail="답변이 생성되지 않았습니다.")

    filename = f"{thread_id}.html"
    output_path = Path("/tmp") / filename
    html_renderer = HtmlRenderer()
    html_content = await html_renderer.render(content=final_answer)
    output_path.write_text(html_content, encoding="utf-8")

    return FileResponse(
        path=output_path,
        filename=filename,
        media_type="text/html",
    )
