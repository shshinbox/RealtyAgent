import asyncio
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from typing import List

from ..auth import get_current_user_id

router = APIRouter()

ALLOWED_CONTENT_TYPES = {"application/pdf"}


def _validate_pdf(file: UploadFile):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400, detail=f"{file.filename}: PDF 파일만 업로드 가능합니다."
        )


@router.post("/upload")
async def upload_document(
    request: Request,
    file: UploadFile,
    user_id: str = Depends(get_current_user_id),
):
    _validate_pdf(file)

    pipeline = request.app.state.pipeline
    chunk_count = await pipeline.ingest(
        file_bytes=await file.read(),
        filename=file.filename,
        metadata={"uploaded_by": user_id, "filename": file.filename},
    )

    return {"filename": file.filename, "chunks_stored": chunk_count}


async def _ingest_one(pipeline, user_id: str, file: UploadFile) -> dict:
    try:
        chunk_count = await pipeline.ingest(
            file_bytes=await file.read(),
            filename=file.filename,
            metadata={"uploaded_by": user_id, "filename": file.filename},
        )
        return {"filename": file.filename, "chunks_stored": chunk_count, "status": "ok"}
    except Exception as e:
        return {"filename": file.filename, "chunks_stored": 0, "status": f"error: {e}"}


@router.post("/upload/batch")
async def upload_documents(
    request: Request,
    files: List[UploadFile],
    user_id: str = Depends(get_current_user_id),
):
    for file in files:
        _validate_pdf(file)

    pipeline = request.app.state.pipeline

    results = await asyncio.gather(*[_ingest_one(pipeline, user_id, f) for f in files])
    total_chunks = sum(r["chunks_stored"] for r in results)

    return {"total_files": len(files), "total_chunks": total_chunks, "files": list(results)}


@router.post("/scan")
async def scan_directory(
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    settings = request.app.state.settings
    docs_dir = settings.DOCS_DIR
    if not docs_dir:
        raise HTTPException(status_code=400, detail="DOCS_DIR이 설정되지 않았습니다.")

    pipeline = request.app.state.pipeline
    result = await pipeline.ingest_directory(
        directory=docs_dir,
        metadata={"indexed_by": user_id},
    )

    return result
