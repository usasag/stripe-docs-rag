from app.retrieval.reranker import rerank_candidates
from app.retrieval.types import RetrievedChunk


def test_reranker_boosts_exact_object_mentions() -> None:
    query = "confirm paymentintent"
    candidates = [
        RetrievedChunk(
            chunk_id="c1",
            document_id="d1",
            title="Accept a payment",
            url="https://docs.stripe.com/payments/accept",
            anchor="confirm",
            content="Confirm the PaymentIntent on the client after collecting details.",
            score=0.70,
            metadata={"product_area": "payments"},
        ),
        RetrievedChunk(
            chunk_id="c2",
            document_id="d2",
            title="Billing overview",
            url="https://docs.stripe.com/billing",
            anchor=None,
            content="Billing overview and invoices.",
            score=0.80,
            metadata={"product_area": "billing"},
        ),
    ]

    reranked = rerank_candidates(query, candidates, top_n=2)

    assert reranked[0].chunk_id == "c1"
    assert reranked[0].rerank_score is not None


def test_reranker_penalizes_code_heavy_chunks_for_conceptual_question() -> None:
    query = "what is a paymentintent"
    candidates = [
        RetrievedChunk(
            chunk_id="code",
            document_id="d1",
            title="Code sample",
            url="https://docs.stripe.com/payments/sample",
            anchor=None,
            content="```python\nfor i in range(200): pass\n```",
            score=0.9,
            metadata={"contains_code": True, "product_area": "payments"},
        ),
        RetrievedChunk(
            chunk_id="concept",
            document_id="d2",
            title="PaymentIntents API",
            url="https://docs.stripe.com/payments/paymentintents",
            anchor=None,
            content="A PaymentIntent tracks payment lifecycle and authentication.",
            score=0.8,
            metadata={"contains_code": False, "product_area": "payments"},
        ),
    ]

    reranked = rerank_candidates(query, candidates, top_n=2)

    assert reranked[0].chunk_id == "concept"
