from __future__ import annotations

from typing import Any


def synthesize_answer(question: str, ranked_results: list[dict[str, Any]], citations: list[dict[str, Any]], confidence: float) -> str:
    if not ranked_results:
        return (
            "I couldn't confidently find a matching Stripe Docs section for that question. "
            "Please narrow the scope (for example: specific product area and object)."
        )

    top = ranked_results[0]
    evidence = top.get('content') or ''
    evidence = ' '.join(str(evidence).split())
    snippet = evidence[:220] + ('...' if len(evidence) > 220 else '')

    if confidence < 0.25:
        return f"Based on limited evidence, here's the best-supported guidance: {snippet}"

    return f"According to Stripe Docs evidence: {snippet}"
