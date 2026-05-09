# PLACEHOLDERS.md

This file tracks every known placeholder / demo-only implementation that should be replaced before production.

## 1) In-memory session persistence instead of Postgres
- Files:
  - `app/agent/session_manager.py`
  - `app/agent/postgres_session_manager.py` *(NEW)*
  - `app/api/deps.py`
- **Status: ✅ RESOLVED**
  - `PostgresSessionManager` created and wired via `deps.py`.
  - Automatically selected when `SUPABASE_DB_URL` is configured.
  - `InMemorySessionManager` remains as fallback for no-DB environments.
  - DB repositories: `SessionRepository`, `MessageRepository` in `app/db/repositories.py`.

## 2) In-memory ingestion index instead of Supabase writes
- Files:
  - `app/ingestion/indexer.py`
  - `app/ingestion/ingest_service.py`
  - `app/api/deps.py`
  - `app/db/postgres_store.py`
- **Status: ✅ RESOLVED**
  - `PostgresIndexer` upserts into `documents` / `document_chunks` with conflict handling.
  - `deps.py` automatically selects DB indexer when `SUPABASE_DB_URL` is present.
  - `InMemoryIndexer` remains as fallback.

## 3) Local hash embedder is not semantic embedding
- Files:
  - `app/ingestion/embedder.py`
- **Status: ✅ RESOLVED**
  - `SentenceTransformerEmbedder` added using `BAAI/bge-small-en-v1.5` (384-dim).
  - Lazy model loading, batched encoding, normalized embeddings.
  - `LocalHashEmbedder` remains for deterministic tests.

## 4) In-memory retriever bypasses pgvector
- Files:
  - `app/retrieval/inmemory_retriever.py`
  - `app/db/postgres_store.py`
  - `app/api/deps.py`
- **Status: ✅ RESOLVED**
  - `PostgresRetriever` queries `match_document_chunks` SQL function.
  - Automatically selected when `SUPABASE_DB_URL` is configured.
  - `InMemoryRetriever` remains as fallback.

## 5) Ingest run endpoint uses hardcoded sample page
- Files:
  - `app/services/ingest_service.py`
  - `app/ingestion/crawler_service.py` *(NEW)*
- **Status: 🟡 PARTIALLY RESOLVED**
  - Async crawler (`crawler_service.py`) implemented with BFS, rate limiting, and error tracking.
  - `IngestOrchestrator.run()` still uses hardcoded sample page for the default path.
  - Replace with: Call `crawl_stripe_docs_sync()` from `IngestOrchestrator` with real seed URLs.

## 6) Eval service is demo smoke, not full benchmark framework
- Files:
  - `app/services/eval_service.py`
  - `app/services/eval_dataset.py` *(NEW)*
  - `app/evals/datasets/qa_goldens.jsonl` *(NEW)*
- **Status: 🟡 PARTIALLY RESOLVED**
  - Eval dataset loader + 15-question golden dataset scaffolded.
  - `EvalService` now persists to `eval_runs` / `eval_results` tables.
  - Still TODO: retrieval metrics (Recall@k/MRR/NDCG), judge path, dataset-driven runners.

## 7) Tool traces and retrieval events not persisted to DB tables
- Files:
  - `app/agent/runtime.py`
  - `app/db/repositories.py` *(NEW)*
- **Status: ✅ RESOLVED**
  - `ToolTraceRepository` and `RetrievalEventRepository` created.
  - `AgentRuntime.chat()` persists traces and events after each turn (non-blocking).

## 8) Chat trace_id mapping in API is pass-through from runtime only
- Files:
  - `app/api/routes_chat.py`
  - `app/api/routes_traces.py` *(NEW)*
- **Status: ✅ RESOLVED**
  - `GET /traces/{session_id}` endpoint added for querying persisted traces.
  - Traces tied to sessions and messages via repository layer.

## 9) Reranker uses heuristic scoring, no real cross-encoder
- Files:
  - `app/retrieval/reranker.py`
  - `app/tools/source_ranker.py`
- **Status: ✅ RESOLVED**
  - `CrossEncoderReranker` added using `cross-encoder/ms-marco-MiniLM-L-6-v2`.
  - Lazy model loading, sigmoid-calibrated scores, model metadata in output.
  - Heuristic reranker preserved as `rerank_candidates()` for fallback/tests.

## 10) Query rewrite/follow-up logic is heuristic-only
- Files:
  - `app/retrieval/query_rewriter.py`
- **Status: 🟠 IMPROVED (placeholder kept open for LLM rewrite)**
  - Expanded follow-up detection: pronoun/deictic analysis, larger phrase set.
  - Context window expanded from 6 to 10 recent messages.
  - Stripe entity vocabulary expanded from 5 to 20+ terms.
  - Future: LLM-backed rewrite behind feature flag.

## 11) Session and ingest/eval stores are process-local dicts
- Files:
  - `app/services/ingest_service.py`
  - `app/services/eval_service.py`
  - `app/db/repositories.py` *(NEW)*
- **Status: ✅ RESOLVED**
  - `IngestJobRepository` and `EvalRunRepository` / `EvalResultRepository` created.
  - Services accept repos via dependency injection, fallback to in-memory stores.

## 12) Model name in runtime is fixed placeholder string
- Files:
  - `app/agent/runtime.py`
  - `app/core/config.py`
- **Status: ✅ RESOLVED**
  - `model_name` is now a `Settings` config field (default: `stripe-docs-rag-v1`).
  - `AgentRuntime` receives model name via constructor, no longer hardcoded.

## 13) Stable IDs use MD5 for ingestion entities
- Files:
  - `app/ingestion/ingest_service.py`
- **Status: ✅ RESOLVED (was already fixed)**
  - Uses `uuid.uuid5(NAMESPACE_URL, ...)` — deterministic UUIDv5, not MD5.

## 14) No Supabase client/repository abstraction wired yet
- Files:
  - `app/db/postgres_store.py`
  - `app/db/connection.py` *(NEW)*
  - `app/db/repositories.py` *(NEW)*
- **Status: ✅ RESOLVED**
  - `ConnectionFactory` provides shared DB access pattern.
  - 7 repositories implemented: Session, Message, ToolTrace, RetrievalEvent, EvalRun, EvalResult, IngestJob.
  - `PostgresIndexer` and `PostgresRetriever` refactored to use `ConnectionFactory`.

## 15) API endpoints are functional vertical slice but not production hardened
- Files:
  - `app/api/middleware.py` *(NEW)*
  - `app/api/auth.py` *(NEW)*
  - `app/core/exceptions.py`
  - `app/main.py`
- **Status: ✅ RESOLVED**
  - `RequestIdMiddleware` — X-Request-Id on every request/response.
  - `ErrorHandlerMiddleware` — domain exceptions → structured JSON error responses.
  - `RateLimitMiddleware` — in-process per-IP token-bucket (30 burst, 0.5/s sustained).
  - `require_auth` — Supabase JWT verification (optional in dev mode).
  - New exception types: `RateLimitError`, `AuthenticationError`, `IngestJobNotFoundError`, `EvalDatasetError`.

---

## Remaining Work
- **#5** — Wire async crawler into `IngestOrchestrator.run()` with real seed URLs.
- **#6** — Implement retrieval metrics (Recall@k, MRR, NDCG), dataset-driven eval runners.
- **#10** — LLM-backed query rewrite path (deferred per decision).

## Notes
- Current implementation is intentionally a working vertical slice for rapid progress.
- Items marked ✅ have production-grade implementations ready for DB integration.
- DB-backed features activate automatically when `SUPABASE_DB_URL` is set in `.env`.
