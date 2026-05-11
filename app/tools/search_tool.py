from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.retrieval.query_rewriter import rewrite_query
from app.retrieval.types import RetrievedChunk


class SearchToolInput(BaseModel):
    query: str = Field(..., description="The search query to execute against the Stripe documentation.")
    top_k: int = Field(8, description="Number of results to retrieve. Default is 8.")
    filters: dict[str, str] | None = Field(None, description="Optional metadata filters (e.g., {'product_area': 'payments'}).")
    session_messages: list[dict[str, Any]] | None = Field(None, description="Recent conversation history for query contextualization.")


class SearchTool:
    def __init__(self, *, retriever: object, chunk_cache: dict[str, RetrievedChunk] | None = None) -> None:
        self.retriever = retriever
        self.chunk_cache = chunk_cache if chunk_cache is not None else {}

    def run(self, tool_input: dict[str, Any] | SearchToolInput) -> dict[str, Any]:
        if isinstance(tool_input, dict):
            parsed_input = SearchToolInput(**tool_input)
        else:
            parsed_input = tool_input

        query_used = rewrite_query(parsed_input.query, session_messages=parsed_input.session_messages or [])
        results = self.retriever.retrieve(query_used, top_k=parsed_input.top_k, filters=parsed_input.filters or {})

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
