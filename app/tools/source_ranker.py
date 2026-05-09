from __future__ import annotations

from typing import Any

from app.retrieval.reranker import rerank_candidates
from app.retrieval.types import RetrievedChunk


class SourceRankerTool:
    def __init__(self, *, chunk_cache: dict[str, RetrievedChunk] | None = None) -> None:
        self.chunk_cache = chunk_cache if chunk_cache is not None else {}

    @staticmethod
    def _from_dict(item: dict[str, Any]) -> RetrievedChunk:
        return RetrievedChunk(
            chunk_id=str(item['chunk_id']),
            document_id=str(item['document_id']),
            title=str(item.get('title', '')),
            url=str(item.get('url', '')),
            anchor=item.get('anchor'),
            content=str(item.get('content', '')),
            score=float(item.get('score', 0.0)),
            metadata=dict(item.get('metadata', {})),
        )

    def run(self, tool_input: dict[str, Any]) -> dict[str, Any]:
        query = str(tool_input.get('query', '')).strip()
        if not query:
            raise ValueError('query is required')

        candidates_raw = tool_input.get('candidates') or []
        candidates = [self._from_dict(c) for c in candidates_raw]

        ranked = rerank_candidates(query, candidates, top_n=max(len(candidates), 1))

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
