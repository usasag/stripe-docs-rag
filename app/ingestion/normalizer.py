from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from app.ingestion.parser import ParsedDocument


@dataclass(frozen=True)
class NormalizedSection:
    section_path: list[str]
    anchor: str | None
    content: str
    contains_code: bool


@dataclass(frozen=True)
class NormalizedDocument:
    url: str
    title: str
    h1: str
    product_area: str
    breadcrumb: list[str]
    metadata: dict[str, str]
    raw_text: str
    sections: list[NormalizedSection]


def _infer_product_area(path: str) -> str:
    parts = [p for p in path.split('/') if p]
    return parts[0] if parts else 'general'


def normalize_document(parsed: ParsedDocument) -> NormalizedDocument:
    parsed_url = urlparse(parsed.url)
    product_area = _infer_product_area(parsed_url.path)

    sections = [
        NormalizedSection(
            section_path=section.section_path,
            anchor=section.anchor,
            content=section.content,
            contains_code='`' in section.content,
        )
        for section in parsed.sections
    ]

    return NormalizedDocument(
        url=parsed.url,
        title=parsed.title,
        h1=parsed.h1,
        product_area=product_area,
        breadcrumb=[],
        metadata={
            'source_domain': parsed_url.netloc,
            'path': parsed_url.path,
            'product_area': product_area,
        },
        raw_text=parsed.raw_text,
        sections=sections,
    )
