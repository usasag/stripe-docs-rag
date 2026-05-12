# Stripe Docs RAG (MCP Server)

This branch exposes the Stripe documentation knowledge base as a native **Claude Desktop tool** via the **Model Context Protocol (MCP)**.

## What this branch is

- **Branch:** `mcp-version`
- **Transport:** MCP `stdio`
- **Server Entrypoint:** `app/mcp_server.py`
- **Main Tool:** `search_stripe_docs(query, top_k=8)`

It uses the same underlying ingestion/retrieval pipeline and Supabase pgvector store as the `master` branch, but integrates as an MCP tool instead of a FastAPI-first chat service.

## Architecture (MCP)

```
Claude Desktop
      │
      ▼
┌─────────────┐    ┌──────────────┐    ┌─────────────────┐
│ MCP Server   │───▶│ Search       │───▶│ pgvector        │
│ (stdio)      │    │ Service      │    │ (Supabase)       │
└─────────────┘    └──────────────┘    └─────────────────┘
      │                    ▲
      └────────────────────┘
        (Returns Markdown)
```

## Prerequisites

- Python 3.10+
- Claude Desktop installed
- A `.env` file with `SUPABASE_DB_URL` configured

## Installation

```bash
pip install -e ".[dev]"
```

Create a local env file from the example:

```bash
cp .env.example .env
```

## Environment Configuration

The app supports branch-specific Supabase overrides. For this branch, you can use either the base variables or the `*_MASTER` overrides (which take precedence):

- `SUPABASE_DB_URL` (or `SUPABASE_DB_URL_MASTER`)

These are already configured in `.env.example` to point to the dedicated technical test database.

## Ingesting the Documentation

This branch includes the same high-quality crawler and ingestion pipeline as `master`:

```bash
python scripts/ingest_all.py
```

The script performs a deep crawl of the live Stripe documentation and upserts semantic chunks into Supabase.

## Claude Desktop Setup (Option C)

1. Open **Claude Desktop** -> **Settings** -> **Developer** -> **Open/Edit Config**.
2. Add this MCP server entry (replace `YOUR_ABSOLUTE_PATH_TO_PROJECT` with the full path to this repository):

```json
{
  "mcpServers": {
    "stripe-docs": {
      "command": "python",
      "args": ["YOUR_ABSOLUTE_PATH_TO_PROJECT/app/mcp_server.py"],
      "cwd": "YOUR_ABSOLUTE_PATH_TO_PROJECT",
      "env": {
        "SUPABASE_DB_URL": "postgresql://readonly_recruiter:temp_30_day_token_123@db.hxmpdytlsejvbkasrhlb.supabase.co:5432/postgres",
        "PYTHONPATH": "YOUR_ABSOLUTE_PATH_TO_PROJECT"
      }
    }
  }
}
```

3. Restart Claude Desktop.
4. Look for the 🔌 icon in the chat bar. You can now ask:
   - "How do I confirm a PaymentIntent using Stripe?"

Claude will automatically call the `search_stripe_docs` tool to find grounded evidence.

## Troubleshooting

- **Tool is not visible:** Confirm your `config.json` is valid JSON and use absolute paths for `cwd` and `PYTHONPATH`. Restart Claude Desktop fully.
- **Connection Error:** Verify `SUPABASE_DB_URL` is reachable and that you have run the migrations/ingestion.
- **Encoding Issues:** This server is pre-configured to force UTF-8 for the `stdio` transport, which is required for Windows compatibility.

## Notes

- This branch focuses on the **deep-dive Option C (MCP Server)**.
- The standard FastAPI RAG service is available on the `master` branch.
