from __future__ import annotations

import re

_WS_RE = re.compile(r"\s+")
_TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")

# Expanded follow-up detection signals
_FOLLOWUP_HINTS = {
    "what about", "and", "also", "how about", "then", "webhooks",
    "but", "instead", "same for", "similar", "likewise", "too",
}

# Pronoun / deictic cues that signal a follow-up
_PRONOUN_CUES = {"it", "its", "they", "them", "this", "that", "those", "these"}

# Expanded Stripe-specific vocabulary
_STRIPE_ENTITIES = {
    'paymentintent', 'checkout', 'setupintent', 'webhooks', 'billing',
    'subscription', 'customer', 'charge', 'refund', 'invoice',
    'payment_method', 'transfer', 'payout', 'balance', 'connect',
    'terminal', 'radar', 'identity', 'tax', 'sigma', 'issuing',
}


def _normalize(text: str) -> str:
    lowered = _WS_RE.sub(' ', text.strip().lower())
    return lowered.rstrip('?.!,;:')


def _keywords(text: str) -> set[str]:
    return {t for t in _TOKEN_RE.findall(text.lower()) if len(t) > 3}


def _is_followup(text: str) -> bool:
    lower = text.lower()
    # Check explicit follow-up phrases
    if any(hint in lower for hint in _FOLLOWUP_HINTS):
        return True
    # Check if starts with follow-up phrase
    if lower.startswith('what about') or lower.startswith('how about'):
        return True
    # Check for pronoun-dominant queries (short queries with pronouns)
    tokens = set(_TOKEN_RE.findall(lower))
    if len(tokens) <= 6 and tokens & _PRONOUN_CUES:
        return True
    return False


def rewrite_query(question: str, session_messages: list[dict[str, str]]) -> str:
    """Rewrite a user question for retrieval, incorporating session context for follow-ups.

    NOTE: This is a heuristic-only implementation. A future version should
    use an LLM rewrite for better disambiguation of complex follow-ups.
    See PLACEHOLDERS.md #10.
    """
    base = _normalize(question)
    if not session_messages:
        return base

    if not _is_followup(base):
        return base

    # Pull signal words from recent user messages (expanded window: last 10).
    recent_user = [
        m.get('content', '')
        for m in session_messages[-10:]
        if m.get('role') == 'user'
    ]
    context_tokens: set[str] = set()
    for msg in recent_user:
        context_tokens.update(_keywords(msg))

    # Keep highly-relevant API nouns (expanded vocabulary).
    prioritized = [
        tok for tok in sorted(context_tokens)
        if tok in _STRIPE_ENTITIES
    ]
    if not prioritized:
        return base

    enriched = f"{' '.join(prioritized)} {base}".strip()
    return _normalize(enriched)
