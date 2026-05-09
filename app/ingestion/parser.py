from __future__ import annotations

from dataclasses import dataclass
from html import unescape
import re


@dataclass(frozen=True)
class ParsedSection:
    section_path: list[str]
    anchor: str | None
    content: str


@dataclass(frozen=True)
class ParsedDocument:
    url: str
    title: str
    h1: str
    sections: list[ParsedSection]
    raw_text: str


_TITLE_RE = re.compile(r'<title[^>]*>(.*?)</title>', re.IGNORECASE | re.DOTALL)
_H1_RE = re.compile(r'<h1[^>]*>(.*?)</h1>', re.IGNORECASE | re.DOTALL)
_HEADING_OR_P_RE = re.compile(
    r'<h([2-4])([^>]*)>(.*?)</h\1>|<p[^>]*>(.*?)</p>',
    re.IGNORECASE | re.DOTALL,
)
_ID_RE = re.compile(r"id=['\"]([^'\"]+)['\"]", re.IGNORECASE)
_TAG_RE = re.compile(r'<[^>]+>')
_WS_RE = re.compile(r'\s+')


def _clean_text(text: str) -> str:
    no_tags = _TAG_RE.sub(' ', text)
    return _WS_RE.sub(' ', unescape(no_tags)).strip()


def parse_html_document(url: str, html: str) -> ParsedDocument:
    title_match = _TITLE_RE.search(html)
    h1_match = _H1_RE.search(html)

    title = _clean_text(title_match.group(1)) if title_match else ''
    h1 = _clean_text(h1_match.group(1)) if h1_match else title

    sections: list[ParsedSection] = []
    current_heading = h1 or title or 'Section'
    current_anchor: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        nonlocal buffer
        content = _WS_RE.sub(' ', ' '.join(buffer)).strip()
        if content:
            sections.append(
                ParsedSection(
                    section_path=[h1 or title or 'Document', current_heading],
                    anchor=current_anchor,
                    content=content,
                )
            )
        buffer = []

    for m in _HEADING_OR_P_RE.finditer(html):
        heading_level, heading_attrs, heading_text, paragraph_text = m.groups()
        if heading_text is not None:
            flush()
            current_heading = _clean_text(heading_text) or current_heading
            id_match = _ID_RE.search(heading_attrs or '')
            current_anchor = id_match.group(1) if id_match else None
        elif paragraph_text is not None:
            cleaned = _clean_text(paragraph_text)
            if cleaned:
                buffer.append(cleaned)

    flush()

    if not sections:
        body_text = _clean_text(html)
        if body_text:
            sections.append(
                ParsedSection(
                    section_path=[h1 or title or 'Document'],
                    anchor=None,
                    content=body_text,
                )
            )

    raw_text = _clean_text(html)
    return ParsedDocument(url=url, title=title or h1, h1=h1 or title, sections=sections, raw_text=raw_text)
