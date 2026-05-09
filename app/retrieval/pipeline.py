from __future__ import annotations

from app.retrieval.citation_builder import build_citations
from app.retrieval.metadata_filters import infer_filters
from app.retrieval.query_rewriter import rewrite_query
from app.retrieval.reranker import rerank_candidates
from app.retrieval.types import RetrievalOutput, RetrievedChunk


def _dedupe_chunks(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    seen: set[tuple[str, str | None, str]] = set()
    out: list[RetrievedChunk] = []
    for c in chunks:
        key = (c.url, c.anchor, ' '.join(c.content.split())[:200])
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out


def _confidence(initial: list[RetrievedChunk], reranked: list[RetrievedChunk]) -> float:
    if not initial or not reranked:
        return 0.0

    top1 = max(min(initial[0].score, 1.0), 0.0)
    first = reranked[0].rerank_score if reranked[0].rerank_score is not None else reranked[0].score
    second = reranked[1].rerank_score if len(reranked) > 1 and reranked[1].rerank_score is not None else (
        reranked[1].score if len(reranked) > 1 else 0.0
    )
    margin = max(first - second, 0.0)
    diversity = len({c.url for c in reranked[:3]}) / max(len(reranked[:3]), 1)

    conf = 0.5 * top1 + 0.3 * min(margin, 1.0) + 0.2 * diversity
    return max(0.0, min(conf, 1.0))


def retrieve_for_question(
    *,
    question: str,
    session_messages: list[dict[str, str]],
    retriever: object,
    top_k_initial: int = 20,
    top_k_final: int = 5,
) -> RetrievalOutput:
    rewritten = rewrite_query(question, session_messages=session_messages)
    filters = infer_filters(rewritten)

    initial_results = retriever.retrieve(rewritten, top_k=top_k_initial, filters=filters)
    reranked = rerank_candidates(rewritten, initial_results, top_n=top_k_final)
    deduped = _dedupe_chunks(reranked)
    citations = build_citations(deduped, max_citations=min(3, top_k_final))

    return RetrievalOutput(
        rewritten_query=rewritten,
        filters=filters,
        initial_results=initial_results,
        reranked_results=deduped,
        citations=citations,
        confidence=_confidence(initial_results, deduped),
    )
