"""
demo.py — Quick demo of the Stripe Docs RAG Agent API.

Run the server first:
    uvicorn app.main:app --reload

Then run this script:
    python scripts/demo.py
"""
import json
import sys

import httpx

BASE_URL = "http://localhost:8000"

QUESTIONS = [
    "What is a PaymentIntent and how do I use it?",
    "How do I handle webhook signature verification?",
    "What is the difference between a PaymentIntent and a SetupIntent?",
]


def ask(question: str) -> dict:
    response = httpx.post(
        f"{BASE_URL}/chat",
        json={"message": question},
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
        print(f"    Make sure uvicorn is running: uvicorn app.main:app --reload")
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
            print(f"         -> {len(result['citations'])} citation(s) | {result['latency_ms']}ms\n")
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
    print(json.dumps(results[0], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
