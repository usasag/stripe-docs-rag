from __future__ import annotations

import os
from typing import Any


def _build_context(ranked_results: list[dict[str, Any]], citations: list[dict[str, Any]]) -> str:
    """Build a grounded context block from retrieved chunks."""
    blocks: list[str] = []
    for i, result in enumerate(ranked_results[:5], 1):
        content = str(result.get('content') or '').strip()
        url = str(result.get('url') or '')
        title = str(result.get('title') or '')
        if content:
            blocks.append(f"[Source {i}] {title}\nURL: {url}\n{content}")
    return '\n\n---\n\n'.join(blocks)


def _call_llm(system: str, user: str) -> str | None:
    """Call the GitHub Models API (gpt-4o-mini) via httpx. Returns None on failure."""
    # Try pydantic Settings first (loads .env), fall back to os.environ
    api_key = os.environ.get('LITELLM_API_KEY')
    if not api_key:
        try:
            from app.core.config import get_settings
            api_key = getattr(get_settings(), 'litellm_api_key', None)
        except Exception:
            pass
    if not api_key:
        return None
    try:
        import httpx
        resp = httpx.post(
            'https://models.inference.ai.azure.com/chat/completions',
            headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
            json={
                'model': 'gpt-4o-mini',
                'messages': [
                    {'role': 'system', 'content': system},
                    {'role': 'user', 'content': user},
                ],
                'max_tokens': 512,
                'temperature': 0.2,
            },
            timeout=20.0,
        )
        resp.raise_for_status()
        return resp.json()['choices'][0]['message']['content'].strip()
    except Exception:
        return None


def synthesize_answer(
    question: str,
    ranked_results: list[dict[str, Any]],
    citations: list[dict[str, Any]],
    confidence: float,
) -> str:
    if not ranked_results:
        return (
            "I couldn't confidently find a matching Stripe Docs section for that question. "
            "Please narrow the scope (for example: specific product area and object)."
        )

    context = _build_context(ranked_results, citations)

    system = (
        "You are a helpful Stripe documentation assistant. "
        "Answer the user's question using ONLY the provided documentation excerpts. "
        "Be concise and specific. If the context doesn't fully answer the question, say so honestly. "
        "Do not make up information not present in the sources."
    )
    user = f"Documentation excerpts:\n\n{context}\n\nQuestion: {question}"

    answer = _call_llm(system, user)
    if answer:
        return answer

    # Graceful fallback: surface the top chunk content directly
    top = ranked_results[0]
    evidence = ' '.join(str(top.get('content') or '').split())
    snippet = evidence[:400] + ('...' if len(evidence) > 400 else '')
    prefix = "Based on limited evidence, here's the best-supported guidance" if confidence < 0.25 else "According to Stripe Docs"
    return f"{prefix}: {snippet}"
