from __future__ import annotations

from app.retrieval.pipeline import retrieve_for_question


class SearchService:
    def __init__(self, *, retriever: object) -> None:
        self.retriever = retriever

    def search(self, *, query: str, top_k: int = 8, session_messages: list[dict[str, str]] | None = None) -> dict[str, object]:
        out = retrieve_for_question(
            question=query,
            session_messages=session_messages or [],
            retriever=self.retriever,
            top_k_initial=max(top_k, 1),
            top_k_final=min(max(top_k, 1), 5),
        )
        return {
            'rewritten_query': out.rewritten_query,
            'filters': out.filters,
            'confidence': out.confidence,
            'results': [
                {
                    'chunk_id': c.chunk_id,
                    'document_id': c.document_id,
                    'title': c.title,
                    'url': c.url,
                    'anchor': c.anchor,
                    'content': c.content,
                    'score': c.score,
                    'rerank_score': c.rerank_score,
                    'metadata': c.metadata,
                }
                for c in out.reranked_results
            ],
            'citations': [
                {
                    'label': c.label,
                    'url': c.url,
                    'snippet': c.snippet,
                    'section_path': c.section_path,
                }
                for c in out.citations
            ],
        }
