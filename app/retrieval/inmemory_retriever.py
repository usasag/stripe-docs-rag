from __future__ import annotations

from app.ingestion.indexer import InMemoryIndexer
from app.retrieval.types import RetrievedChunk


class InMemoryRetriever:
    def __init__(self, *, indexer: InMemoryIndexer) -> None:
        self.indexer = indexer

    @staticmethod
    def _simple_score(query: str, content: str, title: str) -> float:
        q_tokens = {t for t in query.lower().split() if t}
        if not q_tokens:
            return 0.0
        c_tokens = set(content.lower().split()) | set(title.lower().split())
        overlap = len(q_tokens & c_tokens)
        return min(overlap / max(len(q_tokens), 1), 1.0)

    def retrieve(self, query: str, top_k: int, filters: dict[str, str] | None = None) -> list[RetrievedChunk]:
        filters = filters or {}
        out: list[RetrievedChunk] = []

        documents_by_id = {d.id: d for d in self.indexer.documents}
        for chunk in self.indexer.chunks:
            if filters:
                if any(str(chunk.metadata.get(k)) != str(v) for k, v in filters.items()):
                    continue

            doc = documents_by_id.get(chunk.document_id)
            if doc is None:
                continue

            score = self._simple_score(query, chunk.content, doc.title)
            out.append(
                RetrievedChunk(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    title=doc.title,
                    url=doc.source_url,
                    anchor=chunk.anchor,
                    content=chunk.content,
                    score=score,
                    metadata={**chunk.metadata, 'section_path': chunk.section_path},
                )
            )

        out.sort(key=lambda x: x.score, reverse=True)
        return out[: max(top_k, 1)]
