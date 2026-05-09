from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.ingestion.normalizer import NormalizedDocument


@dataclass(frozen=True)
class ChunkRecord:
    chunk_index: int
    section_path: str
    anchor: str | None
    content: str
    token_count: int
    metadata: dict[str, object]


def _tokenize(text: str) -> list[str]:
    return [tok for tok in text.split() if tok]


def _detokenize(tokens: Iterable[str]) -> str:
    return ' '.join(tokens)


def chunk_document_sections(
    doc: NormalizedDocument,
    *,
    target_min_tokens: int = 300,
    target_max_tokens: int = 600,
    overlap_tokens: int = 50,
) -> list[ChunkRecord]:
    if target_min_tokens <= 0 or target_max_tokens <= 0:
        raise ValueError('token targets must be positive')
    if target_min_tokens > target_max_tokens:
        raise ValueError('target_min_tokens must be <= target_max_tokens')

    chunks: list[ChunkRecord] = []
    chunk_idx = 0

    for section in doc.sections:
        tokens = _tokenize(section.content)
        if not tokens:
            continue

        if len(tokens) <= target_max_tokens:
            chunks.append(
                ChunkRecord(
                    chunk_index=chunk_idx,
                    section_path=' > '.join(section.section_path),
                    anchor=section.anchor,
                    content=section.content,
                    token_count=len(tokens),
                    metadata={
                        'product_area': doc.product_area,
                        'contains_code': section.contains_code,
                    },
                )
            )
            chunk_idx += 1
            continue

        step = max(target_max_tokens - overlap_tokens, 1)
        start = 0
        while start < len(tokens):
            end = min(start + target_max_tokens, len(tokens))
            window = tokens[start:end]
            if len(window) < target_min_tokens and end < len(tokens):
                end = min(start + target_min_tokens, len(tokens))
                window = tokens[start:end]

            # Avoid a tiny tail chunk by rebalancing final window.
            if end >= len(tokens) and len(window) < target_min_tokens and len(tokens) > target_max_tokens:
                start = max(len(tokens) - target_max_tokens, 0)
                end = len(tokens)
                window = tokens[start:end]

            chunks.append(
                ChunkRecord(
                    chunk_index=chunk_idx,
                    section_path=' > '.join(section.section_path),
                    anchor=section.anchor,
                    content=_detokenize(window),
                    token_count=len(window),
                    metadata={
                        'product_area': doc.product_area,
                        'contains_code': section.contains_code,
                    },
                )
            )
            chunk_idx += 1

            if end >= len(tokens):
                break
            start += step

    return chunks
