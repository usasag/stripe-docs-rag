from app.retrieval.types import RetrievedChunk
from app.tools.citation_sourcer import CitationSourcerTool
from app.tools.search_tool import SearchTool
from app.tools.source_ranker import SourceRankerTool


class StubRetriever:
    def retrieve(self, query: str, top_k: int, filters: dict[str, str] | None = None):
        return [
            RetrievedChunk(
                chunk_id="c1",
                document_id="d1",
                title="Accept a payment",
                url="https://docs.stripe.com/payments/accept-a-payment",
                anchor="confirm",
                content="Confirm the PaymentIntent to finalize payment.",
                score=0.81,
                metadata={"product_area": "payments", "section_path": "Payments > Accept > Confirm"},
            ),
            RetrievedChunk(
                chunk_id="c2",
                document_id="d2",
                title="Billing",
                url="https://docs.stripe.com/billing",
                anchor=None,
                content="Billing overview.",
                score=0.70,
                metadata={"product_area": "billing", "section_path": "Billing"},
            ),
        ]


def test_search_tool_returns_structured_results() -> None:
    tool = SearchTool(retriever=StubRetriever())

    out = tool.run({"query": "How do I confirm a PaymentIntent?", "top_k": 2, "filters": {"product_area": "payments"}})

    assert out["query_used"].startswith("how do i")
    assert len(out["results"]) == 2
    assert out["results"][0]["chunk_id"] == "c1"


def test_source_ranker_reranks_candidates() -> None:
    candidates = [
        RetrievedChunk(
            chunk_id="c1",
            document_id="d1",
            title="Accept a payment",
            url="https://docs.stripe.com/payments/accept-a-payment",
            anchor="confirm",
            content="Confirm the PaymentIntent to finalize payment.",
            score=0.7,
            metadata={"product_area": "payments"},
        ),
        RetrievedChunk(
            chunk_id="c2",
            document_id="d2",
            title="General docs",
            url="https://docs.stripe.com/docs",
            anchor=None,
            content="General information.",
            score=0.8,
            metadata={"product_area": "general"},
        ),
    ]
    cache = {c.chunk_id: c for c in candidates}
    tool = SourceRankerTool(chunk_cache=cache)

    out = tool.run({"query": "confirm paymentintent", "candidate_chunk_ids": ["c1", "c2"]})

    assert out["ranked_results"][0]["chunk_id"] == "c1"
    assert out["ranked_results"][0]["rerank_score"] >= out["ranked_results"][1]["rerank_score"]


def test_citation_sourcer_builds_citations_from_ranked_chunks() -> None:
    chunks_by_id = {
        "c1": RetrievedChunk(
            chunk_id="c1",
            document_id="d1",
            title="Accept a payment",
            url="https://docs.stripe.com/payments/accept-a-payment",
            anchor="confirm",
            content="Confirm the PaymentIntent to finalize payment.",
            score=0.9,
            metadata={"section_path": "Payments > Accept > Confirm"},
        )
    }
    tool = CitationSourcerTool(chunk_lookup=lambda chunk_id: chunks_by_id.get(chunk_id))

    out = tool.run({"ranked_chunk_ids": ["c1"], "max_citations": 3})

    assert len(out["citations"]) == 1
    assert out["citations"][0]["url"].endswith("#confirm")
