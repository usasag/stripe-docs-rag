# Stripe Docs RAG (MCP Server)

This branch exposes the Stripe documentation knowledge base through a local MCP server so Claude Desktop can call it as a tool.

## What this branch is

- Branch: `mcp-version`
- Transport: MCP `stdio`
- Server entrypoint: `app/mcp_server.py`
- Main tool: `search_stripe_docs(query, top_k=8)`

It uses the same underlying ingestion/retrieval pipeline and Supabase pgvector store as the API branch, but integrates as an MCP tool instead of FastAPI-first chat.

## Prerequisites

- Python 3.10+
- Claude Desktop installed
- A `.env` file with at least:
  - `SUPABASE_DB_URL`

Optional (for eval/judge paths):
- `LLM_API_KEY`

## Installation

```bash
pip install -e ".[dev]"
```

Create env file:

```bash
cp .env.example .env
```

## Ingest Stripe docs (optional, if DB is empty)

This branch includes a crawler/ingest script:

```bash
python scripts/ingest_all.py
```

The script performs a deep crawl and upserts documents/chunks into Supabase.

## Run MCP server locally

From the project root:

```bash
python app/mcp_server.py
```

It runs using `stdio` transport (required by Claude Desktop MCP integration).

## Claude Desktop setup (Option C)

1. Open Claude Desktop -> Settings -> Developer -> Open/Edit Config.
2. Add this MCP server entry (replace `YOUR_ABSOLUTE_PATH_TO_PROJECT`):

```json
{
  "mcpServers": {
    "stripe-docs": {
      "command": "python",
      "args": ["app/mcp_server.py"],
      "cwd": "YOUR_ABSOLUTE_PATH_TO_PROJECT",
      "env": {
        "SUPABASE_DB_URL": "postgresql://readonly_recruiter:***@db.hxmpdytlsejvbkasrhlb.supabase.co:5432/postgres",
        "PYTHONPATH": "YOUR_ABSOLUTE_PATH_TO_PROJECT"
      }
    }
  }
}
```

3. Restart Claude Desktop.
4. Ask Claude something like:
   - "How do I confirm a PaymentIntent using Stripe?"

Claude should automatically call the `search_stripe_docs` tool.

## Troubleshooting

- If tool is not visible:
  - Confirm JSON config is valid.
  - Confirm `cwd` and `PYTHONPATH` are absolute paths.
  - Restart Claude Desktop fully.
- If tool errors on query:
  - Verify `SUPABASE_DB_URL` is reachable.
  - Verify your database has ingested documents.
- If Python import fails:
  - Run from project root or ensure `PYTHONPATH` points to root.

## Notes

- This branch focuses on MCP server integration (technical test Option C).
- The API-oriented branch remains `master`.
