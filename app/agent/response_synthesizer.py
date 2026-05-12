from __future__ import annotations

import os
from typing import Any


def _build_context(ranked_results: list[dict[str, Any]], citations: list[dict[str, Any]]) -> str:
    """Build a grounded context block from retrieved chunks."""
    blocks: list[str] = []
    # Use more evidence to reduce false refusals on broad conceptual questions.
    for i, result in enumerate(ranked_results[:8], 1):
        content = str(result.get("content") or "").strip()
        url = str(result.get("url") or "")
        title = str(result.get("title") or "")
        if content:
            blocks.append(f"[Source {i}] {title}\nURL: {url}\n{content}")
    return "\n\n---\n\n".join(blocks)


def _call_github_models(api_key: str, system: str, user: str, model: str) -> str | None:
    try:
        import httpx

        resp = httpx.post(
            "https://models.inference.ai.azure.com/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "max_tokens": 512,
                "temperature": 0.2,
            },
            timeout=20.0,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


def _call_anthropic(api_key: str, system: str, user: str, model: str) -> str | None:
    try:
        import httpx

        resp = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": 512,
                "temperature": 0.2,
                "system": system,
                "messages": [
                    {"role": "user", "content": user},
                ],
            },
            timeout=20.0,
        )
        resp.raise_for_status()
        data = resp.json()
        parts = data.get("content", [])
        text_parts = [p.get("text", "") for p in parts if p.get("type") == "text"]
        out = "".join(text_parts).strip()
        return out or None
    except Exception:
        return None


def _call_huggingface(api_key: str, system: str, user: str, model: str) -> str | None:
    try:
        import httpx

        resp = httpx.post(
            "https://router.huggingface.co/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "max_tokens": 2048,
                "temperature": 0.2,
            },
            timeout=60.0,
        )
        resp.raise_for_status()
        data = resp.json()
        msg = data["choices"][0]["message"]
        content = (msg.get("content") or "").strip()
        if not content:
            import logging

            logging.getLogger("app.agent.response_synthesizer").warning(
                "HuggingFace returned empty content. reasoning_content=%s finish_reason=%s",
                msg.get("reasoning_content", "")[:200],
                data["choices"][0].get("finish_reason"),
            )
        return content or None
    except Exception:
        import logging

        logging.getLogger("app.agent.response_synthesizer").exception("HuggingFace API call failed")
        return None


def _call_llm(system: str, user: str) -> str | None:
    """Call configured LLM provider. Returns None on failure or missing credentials."""
    try:
        from app.core.config import get_settings

        settings = get_settings()
        provider = (
            (settings.llm_provider or os.environ.get("LLM_PROVIDER") or "github").strip().lower()
        )
        model = (settings.llm_model or os.environ.get("LLM_MODEL") or "gpt-4o-mini").strip()

        github_key = os.environ.get("LITELLM_API_KEY") or settings.litellm_api_key
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY") or settings.anthropic_api_key
        huggingface_key = os.environ.get("HF_API_KEY") or settings.hf_api_key

        if provider == "anthropic":
            key = anthropic_key
            if not key:
                return None
            model = model or "claude-3-5-sonnet-latest"
            return _call_anthropic(key, system, user, model)

        if provider == "huggingface":
            key = huggingface_key
            if not key:
                return None
            model = model or "microsoft/Phi-3-mini-4k-instruct"
            return _call_huggingface(key, system, user, model)

        # default: github models
        key = github_key
        if not key:
            return None
        model = model or "gpt-4o-mini"
        return _call_github_models(key, system, user, model)
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
    evidence = " ".join(str(top.get("content") or "").split())
    snippet = evidence[:400] + ("..." if len(evidence) > 400 else "")
    prefix = (
        "Based on limited evidence, here's the best-supported guidance"
        if confidence < 0.25
        else "According to Stripe Docs"
    )
    return f"{prefix}: {snippet}"
