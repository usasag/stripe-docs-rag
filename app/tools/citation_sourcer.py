from __future__ import annotations

from typing import Any, Callable

from app.retrieval.citation_builder import build_citations
from app.retrieval.types import RetrievedChunk


class CitationSourcerTool:
    def __init__(self, *, chunk_lookup: Callable[[str], RetrievedChunk | None]) -> None:
        self.chunk_lookup = chunk_lookup

    def run(self, tool_input: dict[str, Any]) -> dict[str, Any]:
        ranked_ids = [str(x) for x in (tool_input.get('ranked_chunk_ids') or [])]
        max_citations = int(tool_input.get('max_citations', 3))

        chunks: list[RetrievedChunk] = []
        for cid in ranked_ids:
            chunk = self.chunk_lookup(cid)
            if chunk is not None:
                chunks.append(chunk)

        citations = build_citations(chunks, max_citations=max_citations)
        return {
            'citations': [
                {
                    'label': c.label,
                    'url': c.url,
                    'snippet': c.snippet,
                    'section_path': c.section_path,
                }
                for c in citations
            ]
        }
