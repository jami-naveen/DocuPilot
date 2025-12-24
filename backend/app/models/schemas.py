from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    pdf = "pdf"
    markdown = "markdown"
    text = "text"


class FileUploadResponse(BaseModel):
    blob_name: str
    original_name: str
    size_bytes: int
    container: str


class FileRecord(BaseModel):
    name: str
    size_bytes: int
    uploaded_at: str
    container: str
    status: str = "pending"


class ProcessRequest(BaseModel):
    limit: Optional[int] = Field(default=None, ge=1)


class ProcessStep(BaseModel):
    step: str
    current: int
    total: int


class ProcessStatus(BaseModel):
    job_id: UUID = Field(default_factory=uuid4)
    state: str = "pending"
    steps: List[ProcessStep] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class ChatHistoryItem(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    question: str
    history: List[ChatHistoryItem] = []
    top_k: int = Field(default=5, ge=1, le=20)


class Citation(BaseModel):
    chunk_id: str
    source_document: str
    score: float
    snippet: str


class ChatResponse(BaseModel):
    answer: str
    citations: List[Citation]
    latency_ms: float
    confidence: float

