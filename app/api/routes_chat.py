from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import chat_service_dep
from app.domain.schemas import ChatRequest, ChatResponse

router = APIRouter(tags=['chat'])


@router.post('/chat', response_model=ChatResponse)
def chat(payload: ChatRequest, service=Depends(chat_service_dep)) -> ChatResponse:
    out = service.chat(
        message=payload.message,
        session_id=payload.session_id,
        top_k=payload.top_k,
        max_citations=payload.max_citations,
    )

    trace_id = str(out.get('trace_id', ''))

    return ChatResponse(
        session_id=str(out['session_id']),
        answer=str(out['answer']),
        citations=list(out.get('citations', [])),
        trace_id=trace_id,
        latency_ms=int(out.get('latency_ms', 0)),
    )
