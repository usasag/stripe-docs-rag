from app.retrieval.citation_builder import build_citations
from app.retrieval.types import RetrievedChunk


def test_citation_builder_adds_anchor_urls_and_snippets() -> None:
    chunks = [
        RetrievedChunk(
            chunk_id="c1",
            document_id="d1",
            title="Accept a payment",
            url="https://docs.stripe.com/payments/accept-a-payment",
            anchor="confirm-the-paymentintent",
            content="Confirm the PaymentIntent to finalize payment and handle SCA.",
            score=0.9,
            metadata={"section_path": "Payments > Accept > Confirm"},
            rerank_score=0.95,
        )
    ]

    citations = build_citations(chunks, max_citations=3)

    assert len(citations) == 1
    assert citations[0].url.endswith("#confirm-the-paymentintent")
    assert "Confirm the PaymentIntent" in citations[0].snippet


def test_citation_builder_deduplicates_same_section() -> None:
    chunk = RetrievedChunk(
        chunk_id="c1",
        document_id="d1",
        title="Accept a payment",
        url="https://docs.stripe.com/payments/accept-a-payment",
        anchor="confirm-the-paymentintent",
        content="Confirm the PaymentIntent to finalize payment.",
        score=0.9,
        metadata={"section_path": "Payments > Accept > Confirm"},
    )

    citations = build_citations([chunk, chunk], max_citations=3)

    assert len(citations) == 1
