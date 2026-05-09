from __future__ import annotations


def should_refuse_answer(confidence: float, citations_count: int) -> bool:
    return confidence < 0.15 and citations_count == 0
