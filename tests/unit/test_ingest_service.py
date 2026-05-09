from app.ingestion.crawler import CrawledPage
from app.ingestion.embedder import LocalHashEmbedder
from app.ingestion.indexer import InMemoryIndexer
from app.ingestion.ingest_service import IngestService


def test_ingest_service_processes_pages_end_to_end() -> None:
    page = CrawledPage(
        url="https://docs.stripe.com/payments/accept-a-payment",
        html=(
            "<html><body><main><h1>Accept a payment</h1>"
            "<h2 id='confirm'>Confirm the PaymentIntent</h2>"
            "<p>Confirm the PaymentIntent to finalize payment.</p>"
            "</main></body></html>"
        ),
    )

    indexer = InMemoryIndexer()
    service = IngestService(embedder=LocalHashEmbedder(), indexer=indexer)

    result = service.process_pages([page])

    assert result.pages_seen == 1
    assert result.documents_upserted == 1
    assert result.chunks_upserted >= 1
    assert len(indexer.documents) == 1
    assert len(indexer.chunks) == result.chunks_upserted
