from __future__ import annotations

import re
from typing import Any

from app.retrieval.types import RetrievedChunk

_TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(text)}


def _is_conceptual_query(query: str) -> bool:
    q = query.lower()
    return any(x in q for x in ['what is', 'explain', 'overview', 'used for'])


def _score_candidate(query: str, candidate: RetrievedChunk) -> float:
    score = float(candidate.score)
    q_tokens = _tokens(query)
    content_tokens = _tokens(candidate.content)
    title_tokens = _tokens(candidate.title)

    overlap = len(q_tokens & content_tokens)
    score += min(overlap * 0.03, 0.3)

    # Boost object-name exact mentions.
    for obj in ['paymentintent', 'checkout', 'setupintent', 'webhook']:
        if obj in q_tokens and (obj in content_tokens or obj in title_tokens):
            score += 0.12

    # Boost heading/title alignment.
    if q_tokens & title_tokens:
        score += 0.06

    # Product area alignment.
    pa = str(candidate.metadata.get('product_area', '')).lower()
    if pa and pa in query.lower():
        score += 0.08

    # Penalize code-heavy chunks for conceptual questions.
    contains_code = bool(candidate.metadata.get('contains_code')) or '```' in candidate.content
    if _is_conceptual_query(query) and contains_code:
        score -= 0.18

    return score


def rerank_candidates(query: str, candidates: list[RetrievedChunk], top_n: int = 5) -> list[RetrievedChunk]:
    """Heuristic reranker — rule-based boosts and penalties."""
    rescored: list[RetrievedChunk] = []
    for c in candidates:
        rs = _score_candidate(query, c)
        rescored.append(
            RetrievedChunk(
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                title=c.title,
                url=c.url,
                anchor=c.anchor,
                content=c.content,
                score=c.score,
                metadata=c.metadata,
                rerank_score=rs,
            )
        )

    rescored.sort(key=lambda x: (x.rerank_score if x.rerank_score is not None else x.score), reverse=True)
    return rescored[:max(top_n, 1)]


# ---------------------------------------------------------------------------
# Cross-encoder reranker (production path)
# ---------------------------------------------------------------------------

class CrossEncoderReranker:
    """Production reranker using a sentence-transformers cross-encoder.

    Default model: ``cross-encoder/ms-marco-MiniLM-L-6-v2`` (~22M params, fast).
    Model is lazily loaded on first call.
    """

    def __init__(self, model_name: str = 'cross-encoder/ms-marco-MiniLM-L-6-v2') -> None:
        self.model_name = model_name
        self._model: Any | None = None

    def _load_model(self):
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder  # type: ignore
            except ImportError as exc:
                raise RuntimeError(
                    'sentence-transformers is required for CrossEncoderReranker. '
                    'Install with: pip install sentence-transformers'
                ) from exc
            self._model = CrossEncoder(self.model_name)
        return self._model

    def rerank(
        self,
        query: str,
        candidates: list[RetrievedChunk],
        top_n: int = 5,
    ) -> list[RetrievedChunk]:
        if not candidates:
            return []

        model = self._load_model()
        pairs = [(query, c.content) for c in candidates]
        scores = model.predict(pairs, show_progress_bar=False)

        # Apply sigmoid for calibrated [0, 1] scores
        import math
        calibrated = [1.0 / (1.0 + math.exp(-float(s))) for s in scores]

        rescored: list[RetrievedChunk] = []
        for c, rs in zip(candidates, calibrated):
            rescored.append(
                RetrievedChunk(
                    chunk_id=c.chunk_id,
                    document_id=c.document_id,
                    title=c.title,
                    url=c.url,
                    anchor=c.anchor,
                    content=c.content,
                    score=c.score,
                    metadata={
                        **c.metadata,
                        'reranker_model': self.model_name,
                    },
                    rerank_score=rs,
                )
            )

        rescored.sort(key=lambda x: (x.rerank_score if x.rerank_score is not None else 0.0), reverse=True)
        return rescored[:max(top_n, 1)]
