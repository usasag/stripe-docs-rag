import json

from app.db.postgres_store import PostgresIndexer, PostgresRetriever, vector_literal


class FakeCursor:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchall(self):
        return self.rows

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeConn:
    def __init__(self, rows=None):
        self.cursor_obj = FakeCursor(rows=rows)
        self.commits = 0

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        self.commits += 1

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_vector_literal_formats_pgvector_string() -> None:
    literal = vector_literal([0.1, -0.2, 0.0])
    assert literal == '[0.1,-0.2,0.0]'


def test_postgres_indexer_upsert_document_and_chunks_executes_sql() -> None:
    conn = FakeConn()
    idx = PostgresIndexer(db_url='postgresql://x', connection_factory=lambda: conn)

    idx.upsert_document(
        {
            'id': '00000000-0000-0000-0000-000000000001',
            'source_url': 'https://docs.stripe.com/payments/accept-a-payment',
            'title': 'Accept a payment',
            'h1': 'Accept a payment',
            'product_area': 'payments',
            'raw_text': 'raw',
            'metadata': {'source_domain': 'docs.stripe.com'},
        }
    )

    idx.upsert_chunks(
        [
            {
                'id': '00000000-0000-0000-0000-000000000002',
                'document_id': '00000000-0000-0000-0000-000000000001',
                'chunk_index': 0,
                'section_path': 'Payments > Accept > Confirm',
                'anchor': 'confirm-the-paymentintent',
                'content': 'Confirm the PaymentIntent.',
                'token_count': 4,
                'embedding': [0.1, 0.2, 0.3],
                'metadata': {'product_area': 'payments'},
            }
        ]
    )

    assert conn.commits == 2
    assert len(conn.cursor_obj.executed) == 2


def test_postgres_retriever_maps_rows_to_chunks() -> None:
    rows = [
        (
            '00000000-0000-0000-0000-000000000010',
            '00000000-0000-0000-0000-000000000011',
            'https://docs.stripe.com/payments/accept-a-payment',
            'Accept a payment',
            'Payments > Accept > Confirm',
            'confirm-the-paymentintent',
            'Confirm the PaymentIntent to finalize payment.',
            {'product_area': 'payments'},
            0.91,
        )
    ]
    conn = FakeConn(rows=rows)

    class StubEmbedder:
        def embed_query(self, query: str):
            return [0.1, 0.2, 0.3]

    retriever = PostgresRetriever(
        db_url='postgresql://x',
        embedder=StubEmbedder(),
        connection_factory=lambda: conn,
    )

    chunks = retriever.retrieve('confirm paymentintent', top_k=5, filters={'product_area': 'payments'})

    assert len(chunks) == 1
    assert chunks[0].chunk_id.endswith('0010')
    assert chunks[0].score == 0.91
    # Ensure json filters passed to SQL
    _, params = conn.cursor_obj.executed[0]
    assert json.loads(params[3])['product_area'] == 'payments'
