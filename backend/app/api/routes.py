from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    FileRecord,
    FileUploadResponse,
    ProcessRequest,
    ProcessStatus,
)
from app.services.processing import processing_manager
from app.services.rag import run_rag
from app.services.storage import storage_service
from app.utils.document_loader import guess_mime_type

router = APIRouter(prefix="/api", tags=["rag"])


@router.post("/files/upload", response_model=List[FileUploadResponse])
async def upload_files(files: List[UploadFile] = File(...)) -> List[FileUploadResponse]:
    responses: List[FileUploadResponse] = []
    for file in files:
        contents = await file.read()
        stored = storage_service.upload_file(
            contents,
            blob_name=file.filename,
            content_type=guess_mime_type(file.filename),
        )
        responses.append(
            FileUploadResponse(
                blob_name=stored.name,
                original_name=file.filename,
                size_bytes=stored.size_bytes,
                container=stored.container,
            )
        )
    return responses


@router.get("/files/recent", response_model=List[FileRecord])
def list_recent_files(limit: int = 10) -> List[FileRecord]:
    records = storage_service.list_recent(limit)
    return [
        FileRecord(
            name=r.name,
            size_bytes=r.size_bytes,
            uploaded_at=r.uploaded_at,
            container=r.container,
            status="pending",
        )
        for r in records
    ]


@router.post("/processing/start", response_model=ProcessStatus)
def start_processing(payload: ProcessRequest) -> ProcessStatus:
    job_id = processing_manager.start_job(payload.limit)
    status = processing_manager.get_status(job_id)
    if not status:
        raise HTTPException(status_code=500, detail="Failed to start job")
    return status


@router.get("/processing/{job_id}", response_model=ProcessStatus)
def get_processing_status(job_id: UUID) -> ProcessStatus:
    status = processing_manager.get_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    return status


@router.post("/chat/completions", response_model=ChatResponse)
def chat_completion(payload: ChatRequest) -> ChatResponse:
    return run_rag(payload.question, payload.history, payload.top_k)
