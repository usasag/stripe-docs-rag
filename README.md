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

The `scripts/demo.py` script includes an interactive setup. If no keys are set, it will run `scripts/configure_llm.py` to help you:
1. Choose a provider (`github` or `anthropic`)
2. Enter your API key (validated via a quick test call)
3. Persist the configuration to your `.env` file

#### Supabase env precedence

The app supports branch-specific Supabase overrides. For the `master` branch, `*_MASTER` variables take precedence:

- `SUPABASE_URL_MASTER` (e.g., `https://rmdfvtrdlcvrupukwogu.supabase.co`)
- `SUPABASE_ANON_KEY_MASTER`
- `SUPABASE_SERVICE_ROLE_KEY_MASTER`
- `SUPABASE_DB_URL_MASTER`

These are already configured in `.env.example` to point to a dedicated **master-branch database** for this technical test.

### Ingesting the Documentation

The repository comes pre-indexed, but you can refresh the knowledge base at any time:

```bash
python scripts/ingest_all.py
```

This performs a deep crawl of the live Stripe documentation (using an async crawler with rate-limiting) and upserts semantic chunks into Supabase.

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
