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

### Prerequisites

- Python 3.10+
- A Supabase project with pgvector enabled (or use the provided readonly connection)

### Installation

```bash
pip install -e ".[dev]"
```

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
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "How do I confirm a PaymentIntent?"}'
```

Response includes a synthesized answer, source citations with URLs, and a trace ID for debugging.

## Evaluation

The project includes 15 golden Q&A pairs covering payments, billing, webhooks, testing, and Connect. Run the evaluation suite via:

```bash
curl -X POST http://localhost:8000/evals/run \
  -H "Content-Type: application/json" \
  -d '{"suite_name": "smoke"}'
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
