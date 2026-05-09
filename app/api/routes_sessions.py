from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import session_service_dep
from app.domain.schemas import SessionMessagesResponse, SessionResponse

router = APIRouter(tags=['sessions'])


@router.get('/sessions/{session_id}', response_model=SessionResponse)
def get_session(session_id: str, service=Depends(session_service_dep)) -> SessionResponse:
    return SessionResponse(**service.get_session(session_id))


@router.get('/sessions/{session_id}/messages', response_model=SessionMessagesResponse)
def get_messages(session_id: str, service=Depends(session_service_dep)) -> SessionMessagesResponse:
    return SessionMessagesResponse(session_id=session_id, messages=service.get_messages(session_id))
