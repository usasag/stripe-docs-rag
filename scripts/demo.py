"""
demo.py — Quick demo of the Stripe Docs RAG Agent API.

Run the server first:
    uvicorn app.main:app --reload

Then run this script:
    python scripts/demo.py
"""

import json
import subprocess
import sys
from pathlib import Path

import httpx

BASE_URL = "http://localhost:8000"
ROOT = Path(__file__).resolve().parents[1]

QUESTIONS = [
    "What is a PaymentIntent and how do I use it?",
    "How do I handle webhook signature verification?",
    "What is the difference between a PaymentIntent and a SetupIntent?",
]


def _parse_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def ensure_llm_config() -> None:
    env = _parse_env(ROOT / ".env")
    has_github = bool(env.get("LITELLM_API_KEY", "").strip())
    has_anthropic = bool(env.get("ANTHROPIC_API_KEY", "").strip())
    has_huggingface = bool(env.get("HF_API_KEY", "").strip())
    if has_github or has_anthropic or has_huggingface:
        print("API keys set successfully")
        return

    print("[setup] No LLM API key detected. Starting interactive LLM setup...")
    result = subprocess.run([sys.executable, str(ROOT / "scripts" / "configure_llm.py")])
    if result.returncode != 0:
        print("[ERROR] LLM setup failed. Aborting demo run.")
        sys.exit(result.returncode)


def ask(question: str) -> dict:
    response = httpx.post(
        f"{BASE_URL}/chat",
        json={"message": question, "top_k": 12, "max_citations": 5},
        timeout=60.0,
    )
    response.raise_for_status()
    return response.json()


def format_response(question: str, data: dict) -> dict:
    return {
        "question": question,
        "answer": data["answer"],
        "citations": [
            {
                "label": c["label"],
                "url": c["url"],
                "snippet": c.get("snippet", ""),
            }
            for c in data.get("citations", [])
        ],
        "session_id": data["session_id"],
        "trace_id": data["trace_id"],
        "latency_ms": data["latency_ms"],
    }


def main():
    ensure_llm_config()
    print("=" * 70)
    print("  Stripe Docs RAG Agent — Demo")
    print("=" * 70)

    # Health check first
    try:
        health = httpx.get(f"{BASE_URL}/health", timeout=5.0)
        health.raise_for_status()
        print(f"\n[OK] Server is healthy: {health.json()}\n")
    except Exception as e:
        print(f"\n[ERROR] Could not reach server at {BASE_URL}")
        print("    Make sure uvicorn is running: uvicorn app.main:app --reload")
        print(f"    Error: {e}")
        sys.exit(1)

    results = []
    # Warmup: ensure the embedding model is loaded before timed questions
    print("[warmup] Loading embedding model...")
    try:
        httpx.post(f"{BASE_URL}/chat", json={"message": "ping"}, timeout=90.0)
        print("[warmup] Done.\n")
    except Exception:
        print("[warmup] Skipped.\n")
    for i, question in enumerate(QUESTIONS, 1):
        print(f"[{i}/{len(QUESTIONS)}] Asking: {question!r}")
        try:
            data = ask(question)
            result = format_response(question, data)
            results.append(result)
            print(
                f"         -> {len(result['citations'])} citation(s) | {result['latency_ms']}ms\n"
            )
        except Exception as e:
            print(f"         [FAILED] {e}\n")
            results.append({"question": question, "error": str(e)})

    output_path = "demo_output.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print("=" * 70)
    print(f"[DONE] Full results written to: {output_path}")
    print("=" * 70)
    print()
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")  # type: ignore[assignment]
    print(json.dumps(results[0], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
