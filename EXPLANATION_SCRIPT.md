# Stripe Docs RAG Agent — Recruiter Walkthrough Script

This is the script I’d use while sharing my screen and walking through the codebase with a recruiter.

---

## 1) What this project is

This project is a production-shaped RAG assistant over Stripe documentation.

At a high level, it does four things end to end:
1. Ingest docs content into a vector-ready store model.
2. Retrieve relevant chunks for a user question.
3. Use a managed-agent style tool pipeline with strict Pydantic schemas compatible with Anthropic Tool Use.
4. Expose everything directly to Claude Desktop via a Model Context Protocol (MCP) server, completely eliminating the need for a custom UI.

The architecture is intentionally modular so each layer can be improved independently without rewriting the whole app.

---

## 2) Architecture in one minute

I’d describe it as six layers:

1. MCP Server Layer (`app/mcp_server.py`)  
   Exposes the `search_stripe_docs` tool natively to Claude Desktop via the standard `stdio` transport.

2. Service layer (`app/services/*`)  
   Orchestration use cases (chat, search, ingest, eval, sessions).

3. Agent layer (`app/agent/*`)  
   Session-aware runtime + strict tool registry + guardrails + synthesis.

4. Retrieval layer (`app/retrieval/*`)  
   Query rewrite, metadata filters, rerank, dedupe, confidence, citation assembly.

5. Ingestion layer (`app/ingestion/*`)  
   Parse/normalize/chunk/embed/index docs content.

6. DB layer (`app/db/*`)  
   Schema migration + pgvector SQL function + postgres-backed index/retrieval implementation.

This separation is intentional: it demonstrates design quality and makes each part unit-testable.

---

## 3) Tooling model (Managed Agent style)

The answer pipeline is fixed and auditable, not “magic”.

- `search_tool` (`app/tools/search_tool.py`)  
  Normalizes/re-writes query and retrieves candidates.

- `source_ranker` (`app/tools/source_ranker.py`)  
  Re-ranks candidates and prioritizes direct evidence using ID-based references to save context window tokens.

- `citation_sourcer` (`app/tools/citation_sourcer.py`)  
  Converts ranked chunks into citation objects.

All tools implement strict Pydantic `InputModels` to guarantee native compatibility with the Anthropic Model Context Protocol (MCP).

Agent runtime (`app/agent/runtime.py`) always runs this order:
1. search
2. rank
3. citation
4. synthesize answer

Why this matters:
- Predictable behavior
- Better debugging
- Better recruiter readability
- Clear traceability for evals and failure analysis

---

## 4) How a request flows (/chat)

`POST /chat` flow:

1. Route validates payload (`app/domain/schemas.py`).
2. `ChatService` delegates to `AgentRuntime`.
3. Runtime loads/creates session and stores the user turn.
4. Runtime calls the 3 tools in sequence.
5. Runtime computes confidence + applies guard logic.
6. Runtime synthesizes grounded response + citations.
7. Runtime stores assistant message metadata including traces/retrieval event.
8. API returns `session_id`, `answer`, `citations`, `trace_id`, `latency_ms`.

This gives us a nice balance of product behavior and operational observability.

---

## 5) Retrieval design decisions

The retrieval pipeline is designed around quality over polish:

- Query rewrite for follow-up questions
- Metadata filter inference from query intent
- Candidate retrieval
- Reranking with explicit heuristics
- Deduplication
- Citation packaging
- Confidence score

Why this is good for a technical test:
- Shows I understand retrieval quality is the core of RAG reliability
- Shows architecture for iteration and evaluation
- Keeps model prompting simple and grounded in evidence

---

## 6) Ingestion design decisions

Ingestion responsibilities are explicit:
- Crawl primitives + allowlist handling
- HTML parsing to structured sections
- Normalization + metadata enrichment
- Hierarchical chunking with overlap and size targets
- Embedding abstraction
- Index upsert abstraction

Why it’s designed this way:
- Easy to swap parser/chunker/embedder without touching API/agent layers
- Better testability for each stage
- Lower risk during iteration

---

## 7) Database and vector strategy

The schema includes:
- `documents`
- `document_chunks`
- `sessions`, `messages`, `tool_traces`, `retrieval_events`, `eval_runs`, `eval_results`

And a pgvector search function:
- `match_document_chunks_hybrid(query_embedding, match_count, filters)`

**Security Note:** I specifically provisioned a `readonly_recruiter` database user. This role is strictly limited to `SELECT` queries on the chunks table, allowing anyone reviewing the code to test the MCP server locally without exposing the master database password!

---

## 8) Why this project shape

The code is intentionally split by responsibility:
- Routes stay thin.
- Services orchestrate use cases.
- Retrieval and ingestion stay framework-agnostic.
- Agent orchestration stays explicit and inspectable.

This is “recruiter friendly”: easy to navigate, easy to reason about, and easy to test.

---

## 9) What is tested

The project has unit and integration tests for:
- ingestion components
- retrieval components
- tools
- runtime/session handling
- API route flow
- DB store helper behavior

Current suite validates the vertical slice and protects against regressions while iterating.

---

## 10) Production Hardening (Recently Completed)

We recently executed a 5-wave productionization plan to graduate this project from a prototype slice to a production-ready system. 

### A) Persistence, Observability & Data Access
1. **SQLModel ORM**: Introduced `sqlmodel` for elegant, type-safe CRUD operations over our operational tables (Sessions, Messages, Traces, Events, Evals).
2. **Session Persistence**: Replaced the in-memory session manager with a Postgres-backed implementation.
3. **Traceability**: All agent tool traces and retrieval events are persisted to the database on every turn. Added a `GET /traces/{session_id}` endpoint to expose answer provenance.

### B) Retrieval, Embedding & Hybrid Search
4. **Hybrid Search Integration**: Implemented a Reciprocal Rank Fusion (RRF) pipeline in Postgres fusing our pgvector embeddings with native BM25 `tsvector` full-text search.
5. **Semantic Embeddings**: Upgraded to a production-quality dense retriever (`BAAI/bge-small-en-v1.5`) via `sentence-transformers`.
6. **Cross-Encoder Reranking**: Upgraded to `cross-encoder/ms-marco-MiniLM-L-6-v2` for precise semantic candidate scoring.
7. **Query Rewriting**: Enhanced heuristic follow-up detection with pronoun/deictic analysis and an expanded session context window.

### C) Real Ingestion
8. **Async Crawler**: Replaced the hardcoded demo HTML with a polite, asynchronous HTTP crawler (`httpx`) featuring BFS traversal, rate limiting, and domain-allowlist enforcement.

### D) Evaluation Framework & Resilient Judges
9. **Curated Dataset**: Scaffolded a 15-question golden QA dataset covering factual lookups, conceptual topics, multi-source requirements, and disambiguation.
10. **LLM-as-a-Judge**: Built `LiteLLMJudge` to automatically score agent answers. Configured robust fallback routing (cascading from `gpt-4o` to `llama3` to `mistral` via `litellm`) so evals never crash if an API provider goes down.

### E) MCP Integration (Option C)
11. **Model Context Protocol**: Fully pivoted to an MCP Server (`app/mcp_server.py`) so non-technical users can interact with the Stripe documentation natively through Claude Desktop without needing a custom-built UI.

### What I would do with more time
If I had more time and resources to take this MCP server to a massive production scale, I would focus on:
- **Managed Markdown Crawling (Firecrawl)**: I built a custom async crawler to demonstrate engineering fundamentals, but for true production, I would offload ingestion to a managed service like Firecrawl. It perfectly handles client-side JS rendering and outputs pristine Markdown, preserving Stripe's critical code blocks which dramatically improves embedding accuracy.
- **Remote SSE Deployment**: Currently, the server runs via standard I/O locally. I would deploy the FastMCP server to a cloud provider using Server-Sent Events (SSE), allowing any user to connect their Claude Desktop without needing Python installed locally.
- **Continuous Syncing**: Instead of manual crawling, I would set up cron jobs or listen to Stripe's documentation RSS feeds to automatically upsert new pages and retire deprecated API chunks, ensuring the knowledge base is never stale.
- **Read/Write Agentic Actions**: I would expand the MCP server beyond just documentation retrieval. By allowing users to provide their Stripe Test Mode API Key, the agent could proactively fetch their recent API logs and webhook failures to debug their specific integration issues in real-time.
- **GraphRAG Overlay**: I would build a Knowledge Graph alongside the vector database to explicitly map relationships between complex Stripe entities (e.g., how a `PaymentIntent` relates to a `SetupIntent` or `Customer`), improving retrieval for complex multi-step integration questions.
---

## 11) Final recruiter summary

If I had to summarize this implementation in one sentence:

This is a deliberately structured, testable RAG system that prioritizes retrieval correctness, tool-grounded answers with citations, and clear extension paths toward production hardening.
