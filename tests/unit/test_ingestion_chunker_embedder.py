from app.ingestion.chunker import chunk_document_sections
from app.ingestion.embedder import LocalHashEmbedder
from app.ingestion.normalizer import NormalizedDocument, NormalizedSection


def test_chunker_generates_chunks_in_target_window() -> None:
    text = " ".join(["token"] * 700)
    doc = NormalizedDocument(
        url="https://docs.stripe.com/payments/accept",
        title="Accept",
        h1="Accept",
        product_area="payments",
        breadcrumb=[],
        metadata={},
        raw_text=text,
        sections=[
            NormalizedSection(
                section_path=["Payments", "Accept"],
                anchor="accept",
                content=text,
                contains_code=False,
            )
        ],
    )

    chunks = chunk_document_sections(doc, target_min_tokens=300, target_max_tokens=600, overlap_tokens=50)

    assert len(chunks) >= 2
    assert all(250 <= c.token_count <= 650 for c in chunks)


def test_local_embedder_is_deterministic_and_dimensioned() -> None:
    embedder = LocalHashEmbedder(dimension=384)

    a1 = embedder.embed_query("How do I confirm a PaymentIntent?")
    a2 = embedder.embed_query("How do I confirm a PaymentIntent?")

    assert len(a1) == 384
    assert a1 == a2
