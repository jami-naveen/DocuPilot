from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from threading import Lock
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import get_settings
from app.models.schemas import ProcessStatus, ProcessStep
from app.services.openai_client import openai_client
from app.services.search import search_service
from app.services.storage import storage_service
from app.utils.document_loader import to_text


@dataclass
class ChunkRecord:
    id: str
    content: str
    metadata: dict


class ProcessingManager:
    def __init__(self) -> None:
        self._jobs: Dict[UUID, ProcessStatus] = {}
        self._lock = Lock()
        self._executor = ThreadPoolExecutor(max_workers=2)
        storage_service.ensure_containers()
        search_service.ensure_index()
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=get_settings().processing_chunk_size,
            chunk_overlap=get_settings().processing_chunk_overlap,
        )

    def start_job(self, limit: Optional[int]) -> UUID:
        job_id = uuid4()
        with self._lock:
            self._jobs[job_id] = ProcessStatus(
                job_id=job_id,
                state="queued",
                steps=[
                    ProcessStep(step="filesDiscovered", current=0, total=0),
                    ProcessStep(step="filesProcessed", current=0, total=0),
                    ProcessStep(step="chunksIndexed", current=0, total=0),
                    ProcessStep(step="embeddingsCreated", current=0, total=0),
                ],
            )
        self._executor.submit(self._run_job, job_id, limit)
        return job_id

    def get_status(self, job_id: UUID) -> Optional[ProcessStatus]:
        with self._lock:
            return self._jobs.get(job_id)

    def _run_job(self, job_id: UUID, limit: Optional[int]) -> None:
        status = self._jobs[job_id]
        try:
            status.state = "running"
            raw_files = storage_service.list_unprocessed_blob_names(limit or get_settings().max_documents_per_run)
            self._update_step(job_id, "filesDiscovered", current=len(raw_files), total=len(raw_files))
            self._update_step(job_id, "filesProcessed", current=0, total=len(raw_files))
            total_chunks = 0
            total_embeddings = 0
            for blob_name in raw_files:
                blob = storage_service.download_blob(storage_service.raw_container, blob_name)
                file_bytes = blob.download_blob().readall()
                text = to_text(file_bytes, blob_name)
                chunks = self._splitter.split_text(text)
                chunk_records = self._build_chunk_payloads(blob_name, chunks)
                embeddings = openai_client.batch_embeddings([c.content for c in chunk_records])
                documents = []
                for record, vector in zip(chunk_records, embeddings):
                    doc = {
                        "id": record.id,
                        "content": record.content,
                        "chunk_id": record.metadata["chunk_id"],
                        "source_path": record.metadata["source_path"],
                        "chunk_order": record.metadata["chunk_order"],
                        "metadata": json.dumps(record.metadata),
                        "embedding": vector,
                    }
                    documents.append(doc)
                search_service.upload_documents(documents)
                storage_service.move_blob(
                    storage_service.raw_container,
                    storage_service.processed_container,
                    blob_name,
                )
                total_chunks += len(chunk_records)
                total_embeddings += len(embeddings)
                processed = self._get_step(job_id, "filesProcessed")
                if processed:
                    self._update_step(
                        job_id,
                        "filesProcessed",
                        current=processed.current + 1,
                        total=processed.total,
                    )
                self._update_step(
                    job_id,
                    "chunksIndexed",
                    current=total_chunks,
                    total=total_chunks,
                )
                self._update_step(
                    job_id,
                    "embeddingsCreated",
                    current=total_embeddings,
                    total=total_embeddings,
                )
            status.state = "completed"
        except Exception as exc:  # noqa: BLE001
            status.state = "failed"
            status.errors.append(str(exc))

    def _build_chunk_payloads(self, blob_name: str, chunks: List[str]) -> List[ChunkRecord]:
        payloads: List[ChunkRecord] = []
        safe_blob_name = re.sub(r"[^0-9A-Za-z_\-=]", "-", blob_name)
        for order, chunk in enumerate(chunks):
            chunk_id = f"{safe_blob_name}-{order}"
            payloads.append(
                ChunkRecord(
                    id=chunk_id,
                    content=chunk,
                    metadata={
                        "chunk_id": chunk_id,
                        "source_path": blob_name,
                        "chunk_order": order,
                    },
                )
            )
        return payloads

    def _update_step(
        self,
        job_id: UUID,
        step: str,
        *,
        current: Optional[int] = None,
        total: Optional[int] = None,
    ) -> None:
        with self._lock:
            status = self._jobs[job_id]
            for idx, s in enumerate(status.steps):
                if s.step == step:
                    new_step = ProcessStep(
                        step=step,
                        current=current if current is not None else s.current,
                        total=total if total is not None else s.total,
                    )
                    status.steps[idx] = new_step
                    break

    def _get_step(self, job_id: UUID, step: str) -> Optional[ProcessStep]:
        status = self._jobs[job_id]
        for s in status.steps:
            if s.step == step:
                return s
        return None


processing_manager = ProcessingManager()
