from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import trace_repo_dep, retrieval_event_repo_dep

router = APIRouter(tags=['traces'])


@router.get('/traces/{session_id}')
def get_traces(
    session_id: str,
    trace_repo=Depends(trace_repo_dep),
    retrieval_event_repo=Depends(retrieval_event_repo_dep),
) -> dict[str, object]:
    if trace_repo is None:
        raise HTTPException(status_code=503, detail='Trace persistence not configured (no database)')

    tool_traces = trace_repo.get_traces_for_session(session_id)
    retrieval_events = retrieval_event_repo.get_events_for_session(session_id) if retrieval_event_repo else []

    return {
        'session_id': session_id,
        'tool_traces': tool_traces,
        'retrieval_events': retrieval_events,
    }
