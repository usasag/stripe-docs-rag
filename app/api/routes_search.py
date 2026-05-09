from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import search_service_dep
from app.domain.schemas import SearchRequest, SearchResponse

router = APIRouter(tags=['search'])


@router.post('/search', response_model=SearchResponse)
def search(payload: SearchRequest, service=Depends(search_service_dep)) -> SearchResponse:
    out = service.search(query=payload.query, top_k=payload.top_k)
    return SearchResponse(**out)
