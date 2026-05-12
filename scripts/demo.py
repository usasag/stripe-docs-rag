"""
demo.py — Interactive setup and test for the Stripe Docs MCP Server.

This script:
1. Ensures LLM credentials are configured (required for Evaluations).
2. Runs a sample search using the underlying search service to verify the knowledge base.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

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
    if has_github or has_anthropic:
        print("API keys set successfully")
        return

    print("[setup] No LLM API key detected. Starting interactive LLM setup...")
    print("NOTE: While the MCP server tool is used by Claude Desktop, an API key is required for the Evaluation suite.")
    result = subprocess.run([sys.executable, str(ROOT / "scripts" / "configure_llm.py")])
    if result.returncode != 0:
        print("[ERROR] LLM setup failed. Aborting demo run.")
        sys.exit(result.returncode)


def test_search():
    print("\n[test] Verifying knowledge base retrieval...")
    try:
        # Add root to sys.path so we can import app
        sys.path.insert(0, str(ROOT))
        from app.api.deps import search_service_dep
        
        search_service = search_service_dep()
        query = "How do I confirm a PaymentIntent?"
        print(f"Querying: {query!r}")
        
        out = search_service.search(query=query, top_k=3)
        results = out.get("results", [])
        
        print(f"Found {len(results)} relevant chunks.")
        for i, r in enumerate(results, 1):
            print(f"  {i}. {r.get('title')} ({r.get('url')})")
            
        print("\n✅ Knowledge base is reachable and working.")
    except Exception as e:
        print(f"\n❌ Search test failed: {e}")
        print("   Make sure you have run 'python scripts/ingest_all.py' first.")


def main():
    ensure_llm_config()
    
    print("=" * 70)
    print("  Stripe Docs RAG (MCP Version) — Setup & Demo")
    print("=" * 70)
    
    test_search()
    
    print("\n" + "=" * 70)
    print("NEXT STEPS:")
    print("1. Start the MCP server: python app/mcp_server.py")
    print("2. Connect from Claude Desktop (see README.md for config)")
    print("3. Run evaluations: (Use the Evaluation endpoint in the API branch or run internal eval scripts)")
    print("=" * 70)


if __name__ == "__main__":
    main()
