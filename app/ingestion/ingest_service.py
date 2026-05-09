from __future__ import annotations

from dataclasses import dataclass
import uuid

from app.ingestion.chunker import chunk_document_sections
from app.ingestion.crawler import CrawledPage
from app.ingestion.indexer import IndexedChunk, IndexedDocument
from app.ingestion.normalizer import normalize_document
from app.ingestion.parser import parse_html_document


@dataclass(frozen=True)
class IngestResult:
    pages_seen: int
    documents_upserted: int
    chunks_upserted: int


class IngestService:
    def __init__(self, *, embedder: object, indexer: object) -> None:
        self.embedder = embedder
        self.indexer = indexer

    @staticmethod
    def _stable_id(value: str) -> str:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, value))

    def process_pages(self, pages: list[CrawledPage]) -> IngestResult:
        docs_upserted = 0
        chunks_upserted = 0

        for page in pages:
            parsed = parse_html_document(page.url, page.html)
            normalized = normalize_document(parsed)
            chunks = chunk_document_sections(normalized)
            embeddings = self.embedder.embed_texts([chunk.content for chunk in chunks])

            doc_id = self._stable_id(normalized.url)
            self.indexer.upsert_document(
                IndexedDocument(
                    id=doc_id,
                    source_url=normalized.url,
                    title=normalized.title,
                    h1=normalized.h1,
                    product_area=normalized.product_area,
                    raw_text=normalized.raw_text,
                    metadata=normalized.metadata,
                )
            )
            docs_upserted += 1

            indexed_chunks: list[IndexedChunk] = []
            for chunk, embedding in zip(chunks, embeddings, strict=True):
                chunk_id = self._stable_id(f"{doc_id}:{chunk.chunk_index}:{chunk.content[:48]}")
                indexed_chunks.append(
                    IndexedChunk(
                        id=chunk_id,
                        document_id=doc_id,
                        chunk_index=chunk.chunk_index,
                        section_path=chunk.section_path,
                        anchor=chunk.anchor,
                        content=chunk.content,
                        token_count=chunk.token_count,
                        embedding=embedding,
                        metadata=chunk.metadata,
                    )
                )

            self.indexer.upsert_chunks(indexed_chunks)
            chunks_upserted += len(indexed_chunks)

        return IngestResult(
            pages_seen=len(pages),
            documents_upserted=docs_upserted,
            chunks_upserted=chunks_upserted,
        )
