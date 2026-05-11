from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.retrieval.reranker import rerank_candidates
from app.retrieval.types import RetrievedChunk


class SourceRankerInput(BaseModel):
    query: str = Field(..., description="The original search query used to evaluate relevance.")
    candidate_chunk_ids: list[str] = Field(..., description="List of chunk_ids to rerank.")


class SourceRankerTool:
    def __init__(self, *, chunk_cache: dict[str, RetrievedChunk] | None = None) -> None:
        self.chunk_cache = chunk_cache if chunk_cache is not None else {}

    def run(self, tool_input: dict[str, Any] | SourceRankerInput) -> dict[str, Any]:
        if isinstance(tool_input, dict):
            parsed_input = SourceRankerInput(**tool_input)
        else:
            parsed_input = tool_input

        # Lookup candidates from the cache using IDs instead of parsing full objects
        candidates: list[RetrievedChunk] = []
        for cid in parsed_input.candidate_chunk_ids:
            if cid in self.chunk_cache:
                candidates.append(self.chunk_cache[cid])

        ranked = rerank_candidates(parsed_input.query, candidates, top_n=max(len(candidates), 1))

        ranked_payload = []
        for c in ranked:
            self.chunk_cache[c.chunk_id] = c
            ranked_payload.append(
                {
                    'chunk_id': c.chunk_id,
                    'rerank_score': float(c.rerank_score if c.rerank_score is not None else c.score),
                    'reason': f'reranked by heuristic scoring (base={c.score:.3f})',
                }
            )

        return {'ranked_results': ranked_payload}
