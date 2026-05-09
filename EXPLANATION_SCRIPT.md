# Stripe Docs RAG Agent — Recruiter Walkthrough Script

This is the script I’d use while sharing my screen and walking through the codebase with a recruiter.

---

## 1) What this project is

This project is a production-shaped RAG assistant over Stripe documentation.

At a high level, it does four things end to end:
1. Ingest docs content into a vector-ready store model.
2. Retrieve relevant chunks for a user question.
3. Use a managed-agent style tool pipeline to produce grounded answers with citations.
4. Expose everything through a clean FastAPI API with test coverage and observability.

The architecture is intentionally modular so each layer can be improved independently without rewriting the whole app.

---

## 2) Architecture in one minute

I’d describe it as six layers:

1. API layer (`app/api/*`)  
   Thin routes, typed request/response schemas, dependency wiring.

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

Tools:
- `search_tool` (`app/tools/search_tool.py`)  
  Normalizes/re-writes query and retrieves candidates.

- `source_ranker` (`app/tools/source_ranker.py`)  
  Re-ranks candidates and prioritizes direct evidence.

- `citation_sourcer` (`app/tools/citation_sourcer.py`)  
  Converts ranked chunks into citation objects.

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
- `sessions`
- `messages`
- `tool_traces`
- `retrieval_events`
- `eval_runs`
- `eval_results`

And a pgvector search function:
- `match_document_chunks(query_embedding, match_count, filters)`

This gives a direct path from prototype to production without changing conceptual boundaries.

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

### D) Evaluation Framework
9. **Curated Dataset**: Scaffolded a 15-question golden QA dataset covering factual lookups, conceptual topics, multi-source requirements, and disambiguation.
10. **Metrics-Driven**: Built an eval runner that computes retrieval quality metrics (Recall@k, MRR) against the golden source URLs.

### E) API Hardening & Security
11. **Authentication**: Added Supabase JWT verification (`SUPABASE_ANON_KEY`) for secure endpoint access.
12. **Middleware Stack**: Added `RequestIdMiddleware`, a token-bucket `RateLimitMiddleware`, and an `ErrorHandlerMiddleware` mapping domain exceptions (e.g., `RateLimitError`) to standard HTTP responses.

### What's Left for the Future?
- **LLM-Backed Query Rewrites**: Replacing the heuristic query rewriter with an LLM call for complex multi-turn disambiguation.
- **Judge Models**: Using an LLM-as-a-judge to evaluate faithfulness and citation accuracy in the eval pipeline.

---

## 11) Final recruiter summary

If I had to summarize this implementation in one sentence:

This is a deliberately structured, testable RAG system that prioritizes retrieval correctness, tool-grounded answers with citations, and clear extension paths toward production hardening.
