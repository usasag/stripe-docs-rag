# Stripe Docs RAG Agent

A production-grade **Retrieval-Augmented Generation (RAG) agent** that answers questions about Stripe's official documentation, grounded in real sources with proper citations.

Built with **FastAPI**, **Supabase + pgvector**, and **sentence-transformers**, this project ingests the Stripe documentation site, stores semantically chunked embeddings in a vector database, and exposes an intelligent Q&A agent through a REST API.

## Architecture

```
User Question
      │
      ▼
┌─────────────┐    ┌──────────────┐    ┌─────────────────┐
│  FastAPI     │───▶│ Agent        │───▶│ Search Tool      │
│  /chat       │    │ Runtime      │    │ (pgvector)       │
└─────────────┘    │              │    └─────────────────┘
                   │              │───▶ Source Ranker
                   │              │───▶ Citation Sourcer
                   └──────────────┘
                         │
                         ▼
                   Synthesized Answer
                   + Citations
```

### Core Components

| Component | Description |
|---|---|
| **Ingestion Pipeline** | Async web crawler → HTML parser → Section normalizer → Token-aware chunker → Embedding model → pgvector upsert |
| **Agent Runtime** | Multi-turn session management with a tool registry pattern (search, rank, cite) |
| **Search Tool** | Hybrid vector similarity search against Supabase pgvector |
| **Source Ranker** | Re-ranks retrieved chunks by relevance with confidence scoring |
| **Citation Sourcer** | Extracts and formats source citations with URLs and snippets |
| **Eval Framework** | 15 golden Q&A pairs with MRR, Recall@k, and citation presence metrics |

## Quick Start

> ⚠️ WARNING — TEST KEYS ARE INTENTIONALLY EXPOSED IN THIS REPOSITORY
>
> This repository includes exposed test credentials in `.env.example` on purpose for technical-test simplicity.
>
> I am fully aware this is not secure and must never be done in production.
>
> In no way, shape, or form should these keys be exposed in any real production environment.
>
> For real deployments, use secure secret management and rotate all credentials.

### Prerequisites

- Python 3.10+
- A Supabase project with pgvector enabled (or use the provided readonly connection)

### Installation

```bash
pip install -e ".[dev]"
```

### Environment configuration

Create a local env file from the example:

```bash
cp .env.example .env
```

#### LLM provider setup

This project supports two providers for answer synthesis:

- `github` (GitHub Models API)
- `anthropic` (Claude API)

Set in `.env`:

- `LLM_PROVIDER` = `github` or `anthropic`
- `LLM_MODEL` is set automatically by setup (hardcoded per provider):
  - GitHub -> `gpt-4o-mini`
  - Anthropic -> `claude-sonnet-4-5-20250929`
- `LITELLM_API_KEY` for GitHub provider
- `ANTHROPIC_API_KEY` for Anthropic provider

If you run `python scripts/demo.py` with no API keys set, the script will:

1. Ask you to choose a provider (`github` or `anthropic`)
2. Inform you of the fixed model for that provider
3. Ask for your API key
4. Validate the key with a quick provider API call
5. Persist `LLM_PROVIDER`, `LLM_MODEL`, and key into `.env`

If an API key is already set, it prints: `API keys set successfully`.

#### Supabase env precedence

The app loads settings from `.env` and supports branch-specific Supabase overrides.
For each Supabase field, `*_MASTER` takes precedence over the base variable:

- `SUPABASE_URL_MASTER` -> `SUPABASE_URL`
- `SUPABASE_ANON_KEY_MASTER` -> `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY_MASTER` -> `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_DB_URL_MASTER` -> `SUPABASE_DB_URL`

If you are only using one environment, set the base variables.
If you are working on `master` while keeping another branch configured, set both and use the `*_MASTER` values for this branch.

### Running the API

```bash
uvicorn app.main:app --reload
```

The server starts at `http://localhost:8000`. Database migrations run automatically on startup.

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/chat` | Ask a question with multi-turn session support |
| `POST` | `/search` | Raw semantic search over the knowledge base |
| `POST` | `/ingest/run` | Trigger documentation crawl and ingestion |
| `GET` | `/ingest/status/{job_id}` | Check ingestion job status |
| `POST` | `/evals/run` | Run the evaluation suite |
| `GET` | `/evals/latest` | Get latest evaluation results |
| `GET` | `/sessions/{id}` | Retrieve session history |

### Example: Ask a Question

```bash
curl.exe -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{"message": "How do I confirm a PaymentIntent?"}'
```

Response includes a synthesized answer, source citations with URLs, and a trace ID for debugging.

### Demo Script

Alternatively, run the included demo script to query 3 representative questions and write the full structured JSON output to `demo_output.json` — no curl required:

```bash
python scripts/demo.py
```

## Evaluation

The project includes 15 golden Q&A pairs covering payments, billing, webhooks, testing, and Connect. Run the evaluation suite via:

```bash
curl.exe -X POST http://localhost:8000/evals/run -H "Content-Type: application/json" -d '{"suite_name": "smoke"}'
```

Metrics tracked:
- **Citation Presence** — Does the agent cite at least one source?
- **MRR (Mean Reciprocal Rank)** — How highly is the correct source ranked?
- **Recall@k** — Are the gold source URLs present in the retrieved results?

## Branches

| Branch | Description |
|--------|-------------|
| `master` | Base FastAPI version — meets all core requirements |
| `mcp-version` | Deep dive into **Option C (MCP Server)** — exposes the knowledge base as a native Claude Desktop tool via the Model Context Protocol |

## Health Check

`GET /health` returns `{"status": "ok"}`.
