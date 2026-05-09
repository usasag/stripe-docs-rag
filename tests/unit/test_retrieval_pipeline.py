from app.retrieval.pipeline import retrieve_for_question
from app.retrieval.types import RetrievedChunk


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
                score=0.82,
                metadata={"product_area": "payments", "section_path": "Payments > Accept"},
            ),
            RetrievedChunk(
                chunk_id="c2",
                document_id="d2",
                title="Accept a payment",
                url="https://docs.stripe.com/payments/accept-a-payment",
                anchor="confirm",
                content="Confirm the PaymentIntent to finalize payment.",
                score=0.8,
                metadata={"product_area": "payments", "section_path": "Payments > Accept"},
            ),
        ]


def test_retrieve_pipeline_rewrites_filters_reranks_and_dedupes() -> None:
    out = retrieve_for_question(
        question="What about webhooks?",
        session_messages=[{"role": "user", "content": "How do I confirm a PaymentIntent?"}],
        retriever=StubRetriever(),
        top_k_initial=20,
        top_k_final=5,
    )

    assert "webhooks" in out.rewritten_query
    assert len(out.initial_results) == 2
    assert len(out.reranked_results) == 1
    assert len(out.citations) == 1
    assert 0 <= out.confidence <= 1
