from __future__ import annotations

from typing import Any

from app.retrieval.query_rewriter import rewrite_query
from app.retrieval.types import RetrievedChunk


class SearchTool:
    def __init__(self, *, retriever: object, chunk_cache: dict[str, RetrievedChunk] | None = None) -> None:
        self.retriever = retriever
        self.chunk_cache = chunk_cache if chunk_cache is not None else {}

    def run(self, tool_input: dict[str, Any]) -> dict[str, Any]:
        query = str(tool_input.get('query', '')).strip()
        if not query:
            raise ValueError('query is required')

        top_k = int(tool_input.get('top_k', 8))
        filters = tool_input.get('filters') or {}
        session_messages = tool_input.get('session_messages') or []

        query_used = rewrite_query(query, session_messages=session_messages)
        results = self.retriever.retrieve(query_used, top_k=top_k, filters=filters)

        payload: list[dict[str, Any]] = []
        for r in results:
            self.chunk_cache[r.chunk_id] = r
            payload.append(
                {
                    'chunk_id': r.chunk_id,
                    'document_id': r.document_id,
                    'title': r.title,
                    'url': r.url,
                    'anchor': r.anchor,
                    'content': r.content,
                    'score': r.score,
                    'metadata': r.metadata,
                }
            )

        return {
            'query_used': query_used,
            'results': payload,
        }
