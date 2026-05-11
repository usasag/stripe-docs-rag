from __future__ import annotations

import json
from typing import Any, Callable

from app.db.connection import ConnectionFactory
from app.retrieval.types import RetrievedChunk


def vector_literal(values: list[float]) -> str:
    return '[' + ','.join(str(float(v)) for v in values) + ']'


def _get(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


class PostgresIndexer:
    def __init__(self, *, db_url: str = '', connection_factory: Callable[[], Any] | None = None) -> None:
        self.db_url = db_url
        self.cf = ConnectionFactory(db_url=db_url, connection_factory=connection_factory)

    def _connect(self):
        return self.cf.connect()

    def upsert_document(self, document: Any) -> None:
        sql = """
        insert into documents (id, source_url, source_domain, title, h1, product_area, raw_text, metadata)
        values (%s::uuid, %s, %s, %s, %s, %s, %s, %s::jsonb)
        on conflict (source_url) do update set
            title = excluded.title,
            h1 = excluded.h1,
            product_area = excluded.product_area,
            raw_text = excluded.raw_text,
            metadata = excluded.metadata,
            updated_at = now();
        """

        metadata = _get(document, 'metadata', {}) or {}
        params = (
            str(_get(document, 'id')),
            str(_get(document, 'source_url')),
            str(metadata.get('source_domain', 'docs.stripe.com')),
            str(_get(document, 'title', '') or ''),
            str(_get(document, 'h1', '') or ''),
            str(_get(document, 'product_area', '') or ''),
            str(_get(document, 'raw_text', '') or ''),
            json.dumps(metadata),
        )

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
            conn.commit()

    def upsert_chunks(self, chunks: list[Any]) -> None:
        sql = """
        insert into document_chunks (
            id, document_id, chunk_index, section_path, anchor, content, token_count, embedding, metadata
        )
        values (%s::uuid, %s::uuid, %s, %s, %s, %s, %s, %s::vector(384), %s::jsonb)
        on conflict (document_id, chunk_index) do update set
            content = excluded.content,
            token_count = excluded.token_count,
            embedding = excluded.embedding,
            metadata = excluded.metadata;
        """

        with self._connect() as conn:
            with conn.cursor() as cur:
                for chunk in chunks:
                    params = (
                        str(_get(chunk, 'id')),
                        str(_get(chunk, 'document_id')),
                        int(_get(chunk, 'chunk_index', 0)),
                        str(_get(chunk, 'section_path', '') or ''),
                        _get(chunk, 'anchor'),
                        str(_get(chunk, 'content', '') or ''),
                        int(_get(chunk, 'token_count', 0)),
                        vector_literal(list(_get(chunk, 'embedding', []))),
                        json.dumps(_get(chunk, 'metadata', {}) or {}),
                    )
                    cur.execute(sql, params)
            conn.commit()


class PostgresRetriever:
    def __init__(
        self,
        *,
        db_url: str = '',
        embedder: Any,
        connection_factory: Callable[[], Any] | None = None,
    ) -> None:
        self.db_url = db_url
        self.embedder = embedder
        self.cf = ConnectionFactory(db_url=db_url, connection_factory=connection_factory)

    def _connect(self):
        return self.cf.connect()

    def retrieve(self, query: str, top_k: int, filters: dict[str, str] | None = None) -> list[RetrievedChunk]:
        embedding = self.embedder.embed_query(query)
        emb_literal = vector_literal(embedding)

        sql = """
        select
            chunk_id,
            document_id,
            source_url,
            title,
            section_path,
            anchor,
            content,
            metadata,
            similarity
        from match_document_chunks_hybrid(%s, %s::vector(384), %s, %s::jsonb)
        ;
        """

        params = (query, emb_literal, int(top_k), json.dumps(filters or {}))

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                rows = list(cur.fetchall())

        out: list[RetrievedChunk] = []
        for row in rows:
            out.append(
                RetrievedChunk(
                    chunk_id=str(row[0]),
                    document_id=str(row[1]),
                    title=str(row[3]),
                    url=str(row[2]),
                    anchor=str(row[5]) if row[5] is not None else None,
                    content=str(row[6]),
                    score=float(row[8]),
                    metadata={**(row[7] or {}), 'section_path': row[4]},
                )
            )
        return out
