from __future__ import annotations

from app.retrieval.types import Citation, RetrievedChunk


def _snippet(text: str, max_chars: int = 420) -> str:
    clean = ' '.join(text.split())
    if len(clean) <= max_chars:
        return clean
    return clean[: max_chars - 3].rstrip() + '...'


def build_citations(chunks: list[RetrievedChunk], max_citations: int = 3) -> list[Citation]:
    out: list[Citation] = []
    seen: set[tuple[str, str | None]] = set()

    for c in chunks:
        key = (c.url, c.anchor)
        if key in seen:
            continue
        seen.add(key)

        url = c.url if not c.anchor else f"{c.url}#{c.anchor}"
        out.append(
            Citation(
                label=f"Stripe Docs - {c.title}",
                url=url,
                snippet=_snippet(c.content),
                section_path=str(c.metadata.get('section_path')) if c.metadata.get('section_path') else None,
            )
        )
        if len(out) >= max_citations:
            break

    return out
