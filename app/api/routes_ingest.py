from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import ingest_service_dep
from app.domain.schemas import IngestRunRequest, IngestRunResponse, IngestStatusResponse

router = APIRouter(tags=['ingest'])


@router.post('/ingest/run', response_model=IngestRunResponse)
def run_ingest(payload: IngestRunRequest, service=Depends(ingest_service_dep)) -> IngestRunResponse:
    out = service.run(payload.scope)
    return IngestRunResponse(**out)


@router.get('/ingest/status/{job_id}', response_model=IngestStatusResponse)
def ingest_status(job_id: str, service=Depends(ingest_service_dep)) -> IngestStatusResponse:
    out = service.status(job_id)
    return IngestStatusResponse(**out)
