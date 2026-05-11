from __future__ import annotations

from typing import Any, Callable

from pydantic import BaseModel, Field

from app.retrieval.citation_builder import build_citations
from app.retrieval.types import RetrievedChunk


class CitationSourcerInput(BaseModel):
    ranked_chunk_ids: list[str] = Field(..., description="List of ranked chunk_ids to build citations for.")
    max_citations: int = Field(3, description="Maximum number of citations to generate. Default is 3.")


class CitationSourcerTool:
    def __init__(self, *, chunk_lookup: Callable[[str], RetrievedChunk | None]) -> None:
        self.chunk_lookup = chunk_lookup

    def run(self, tool_input: dict[str, Any] | CitationSourcerInput) -> dict[str, Any]:
        if isinstance(tool_input, dict):
            parsed_input = CitationSourcerInput(**tool_input)
        else:
            parsed_input = tool_input

        ranked_ids = parsed_input.ranked_chunk_ids
        max_citations = parsed_input.max_citations

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
