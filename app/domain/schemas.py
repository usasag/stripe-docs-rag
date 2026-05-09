from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = 8


class SearchResultItem(BaseModel):
    chunk_id: str
    document_id: str
    title: str
    url: str
    anchor: str | None = None
    content: str
    score: float
    rerank_score: float | None = None
    metadata: dict[str, object]


class CitationItem(BaseModel):
    label: str
    url: str
    snippet: str
    section_path: str | None = None


class SearchResponse(BaseModel):
    rewritten_query: str
    filters: dict[str, str]
    confidence: float
    results: list[SearchResultItem]
    citations: list[CitationItem]


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str = Field(min_length=1)
    top_k: int = 8
    max_citations: int = 3


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    citations: list[CitationItem]
    trace_id: str
    latency_ms: int


class IngestRunRequest(BaseModel):
    scope: str = 'payments'


class IngestRunResponse(BaseModel):
    job_id: str
    status: str
    pages_seen: int
    documents_upserted: int
    chunks_upserted: int


class IngestStatusResponse(BaseModel):
    job_id: str
    status: str
    pages_seen: int
    documents_upserted: int
    chunks_upserted: int


class SessionResponse(BaseModel):
    session_id: str
    message_count: int
    status: str


class SessionMessagesResponse(BaseModel):
    session_id: str
    messages: list[dict[str, object]]


class EvalRunRequest(BaseModel):
    suite_name: str = 'smoke'


class EvalRunResponse(BaseModel):
    eval_run_id: str | None
    suite_name: str | None
    summary: dict[str, object]


class EvalLatestResponse(BaseModel):
    eval_run_id: str | None
    suite_name: str | None
    summary: dict[str, object]
