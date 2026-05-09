from __future__ import annotations

from typing import Protocol

from app.retrieval.types import RetrievedChunk


class Retriever(Protocol):
    def retrieve(self, query: str, top_k: int, filters: dict[str, str] | None = None) -> list[RetrievedChunk]: ...
