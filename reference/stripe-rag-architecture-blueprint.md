# Stripe Docs RAG Agent Architecture Blueprint

## Goal
Build a production-shaped technical test submission that answers questions over Stripe documentation using Supabase + pgvector, exposes a small FastAPI API, and goes deeper on **Option A: Managed Agent Q&A** with a Claude Managed Agent style architecture, persistent sessions, and three custom tools: `search_tool`, `citation_sourcer`, and `source_ranker`.[file:1]

The blueprint is intentionally designed for a 4–6 hour implementation window while preserving a scalable architecture. The submitted version should prioritize a thin vertical slice that works end to end, but every boundary in this document should support future hardening without a rewrite.[file:1]

## Scope fit
The technical test requires four baseline capabilities: ingesting a public documentation site into a vector store, answering with citations, exposing a FastAPI endpoint, and including an evaluation method. It also asks the candidate to pick one deeper path; this plan selects Option A and expands it with proper session management and custom tools.[file:1]

Stripe Docs is a strong target because it is public, technical, multi-page, and citation-sensitive. It also creates realistic evaluation scenarios around API concepts, payments terminology, implementation guides, and edge-case ambiguity.[cite:1]

## Architecture principles
- Ship an end-to-end vertical slice first.
- Keep domain logic framework-agnostic.
- Make retrieval measurable before making generation fancy.
- Store enough traces to debug retrieval quality, tool behavior, and answer quality.
- Optimize for recruiter readability: clear Python, explicit contracts, visible tradeoffs.
- Use local/open-source retrieval components where practical to control eval cost.

## Solution overview
The system has five layers:

1. **Ingestion pipeline**: crawl Stripe docs, normalize content, chunk intelligently, embed chunks, and store them in Supabase Postgres with pgvector.
2. **Retrieval layer**: hybrid-ish retrieval centered on vector search plus metadata filtering, followed by local reranking.
3. **Agent layer**: a managed-agent-inspired orchestration loop that can call three tools, preserve thread state, and produce grounded answers with citations.
4. **API layer**: FastAPI endpoints for ingestion status, search, chat, session history, and eval execution.
5. **Evaluation layer**: offline retrieval/generation evals, LLM-as-judge and heuristic checks, regression datasets, and CI quality gates.[file:1]

## High-level flow
```text
Stripe Docs -> crawler -> cleaner -> chunker -> embeddings -> Supabase/pgvector
                                                           |
User -> FastAPI -> agent runtime -> tools -> retrieval -> reranker -> citation assembly -> answer
                                                           |
                                                traces, sessions, eval logs -> Supabase Postgres
```

## Repository blueprint
```text
stripe-docs-rag/
├── app/
│   ├── api/
│   │   ├── deps.py
│   │   ├── routes_health.py
│   │   ├── routes_chat.py
│   │   ├── routes_search.py
│   │   ├── routes_sessions.py
│   │   ├── routes_ingest.py
│   │   └── routes_evals.py
│   ├── core/
│   │   ├── config.py
│   │   ├── logging.py
│   │   ├── telemetry.py
│   │   └── exceptions.py
│   ├── db/
│   │   ├── supabase.py
│   │   ├── pgvector_queries.py
│   │   ├── models.py
│   │   └── migrations/
│   ├── domain/
│   │   ├── entities.py
│   │   ├── schemas.py
│   │   └── contracts.py
│   ├── ingestion/
│   │   ├── crawler.py
│   │   ├── parser.py
│   │   ├── normalizer.py
│   │   ├── chunker.py
│   │   ├── embedder.py
│   │   ├── indexer.py
│   │   └── ingest_service.py
│   ├── retrieval/
│   │   ├── query_rewriter.py
│   │   ├── retriever.py
│   │   ├── reranker.py
│   │   ├── metadata_filters.py
│   │   └── citation_builder.py
│   ├── agent/
│   │   ├── runtime.py
│   │   ├── prompts.py
│   │   ├── session_manager.py
│   │   ├── tool_registry.py
│   │   ├── response_synthesizer.py
│   │   └── guards.py
│   ├── tools/
│   │   ├── search_tool.py
│   │   ├── citation_sourcer.py
│   │   └── source_ranker.py
│   ├── evals/
│   │   ├── datasets/
│   │   │   ├── qa_goldens.jsonl
│   │   │   └── retrieval_goldens.jsonl
│   │   ├── runners/
│   │   │   ├── retrieval_eval.py
│   │   │   ├── generation_eval.py
│   │   │   ├── judge_eval.py
│   │   │   └── regression_suite.py
│   │   ├── metrics.py
│   │   ├── report.py
│   │   └── fixtures.py
│   ├── services/
│   │   ├── chat_service.py
│   │   ├── search_service.py
│   │   ├── session_service.py
│   │   └── eval_service.py
│   └── main.py
├── scripts/
│   ├── ingest_stripe_docs.py
│   ├── run_evals.py
│   └── seed_eval_dataset.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── smoke/
├── docs/
│   ├── architecture.md
│   ├── api.md
│   ├── evals.md
│   └── tradeoffs.md
├── .env.example
├── README.md
├── pyproject.toml
└── Makefile
```

## Why this project shape
This repo layout separates API wiring from agent logic, retrieval logic, and ingestion logic. That makes the FastAPI surface easy to review while keeping the managed-agent path reusable if the same retrieval stack is later exposed through another interface such as Slack, a UI, or an MCP server.[file:1]

It also makes AI coding assistants more effective because each file has a narrow responsibility, stable interfaces, and easy-to-prompt implementation boundaries. That reduces agent drift and lowers the chance of mixed concerns across routing, storage, retrieval, and evaluation.

## Core components

### 1. Ingestion pipeline
The ingestion path should be deliberately simple but production-shaped:

- Crawl Stripe docs starting from a configured set of seeds, for example the docs home page and selected product sections.
- Restrict to allowed domains and canonical docs paths.
- Parse HTML to structured markdown-like text.
- Preserve page metadata: `url`, `title`, `h1`, section headings, last crawled time, breadcrumb, product area, and anchor IDs.
- Chunk by semantic boundaries first, then by token budget.
- Embed each chunk with a local embedding model.
- Upsert into Supabase `documents` and `document_chunks` tables.

### 2. Retrieval stack
The retrieval pipeline should use:

- Query normalization and optional rewrite for conversational follow-ups.
- Vector similarity search in pgvector.
- Metadata filtering by product area, doc type, or URL path when the query implies it.
- Local reranking with a cross-encoder or lightweight reranker.
- Deduplication by page and section.
- Citation packaging with URL + section anchors + snippet spans.

### 3. Agent runtime
The managed-agent-inspired runtime should support:

- Multi-turn sessions persisted in Postgres.
- Tool calling with a strict registry.
- Structured trace capture for every tool invocation.
- Answer grounding requirements: every factual answer must cite retrieved sources.
- Fallback handling when retrieval confidence is weak.
- Session-aware question rewriting for follow-up questions.

### 4. API surface
FastAPI should not be just a thin `/chat` endpoint. It should expose reviewer-friendly endpoints that prove Python design skill and make debugging easy:

- `/health`
- `/ingest/run`
- `/ingest/status/{job_id}`
- `/search`
- `/chat`
- `/sessions/{session_id}`
- `/sessions/{session_id}/messages`
- `/evals/run`
- `/evals/latest`

### 5. Evaluation system
The eval layer is the most important quality lever in the whole project. The architecture should assume retrieval and answer quality will be wrong by default until measured, segmented, and improved.[file:1]

## Data model

### Primary tables

#### `documents`
Stores page-level canonical document metadata.

| Column | Type | Notes |
|---|---|---|
| id | uuid | PK |
| source_url | text | Canonical Stripe docs URL |
| source_domain | text | `docs.stripe.com` |
| title | text | Page title |
| h1 | text | Main heading |
| breadcrumb | jsonb | Structured nav path |
| product_area | text | e.g. payments, billing, webhooks |
| content_hash | text | Change detection |
| raw_text | text | Optional for debugging |
| metadata | jsonb | Extra fields |
| created_at | timestamptz | Audit |
| updated_at | timestamptz | Audit |

#### `document_chunks`
Stores chunk-level retrieval records.

| Column | Type | Notes |
|---|---|---|
| id | uuid | PK |
| document_id | uuid | FK to documents |
| chunk_index | int | Stable within document |
| section_path | text | Heading path |
| anchor | text | URL fragment if available |
| content | text | Chunk text |
| token_count | int | Chunk sizing |
| embedding | vector | pgvector column |
| metadata | jsonb | filterable metadata |
| created_at | timestamptz | Audit |

#### `sessions`
Conversation thread registry.

| Column | Type | Notes |
|---|---|---|
| id | uuid | PK |
| external_session_id | text | Optional public ID |
| user_label | text | Optional demo label |
| status | text | active, archived |
| created_at | timestamptz | Audit |
| updated_at | timestamptz | Audit |

#### `messages`
User and assistant messages.

| Column | Type | Notes |
|---|---|---|
| id | uuid | PK |
| session_id | uuid | FK |
| role | text | user, assistant, system |
| content | text | Message body |
| turn_index | int | Ordered thread position |
| model_name | text | Useful for eval drift |
| metadata | jsonb | latency, token counts, etc. |
| created_at | timestamptz | Audit |

#### `tool_traces`
Full observability for tool calls.

| Column | Type | Notes |
|---|---|---|
| id | uuid | PK |
| session_id | uuid | FK |
| message_id | uuid | FK to triggering message |
| tool_name | text | search, rank, cite |
| tool_input | jsonb | Tool args |
| tool_output | jsonb | Tool result summary |
| latency_ms | int | Performance |
| success | boolean | Monitoring |
| created_at | timestamptz | Audit |

#### `retrieval_events`
Captures retrieval internals for evals and debugging.

| Column | Type | Notes |
|---|---|---|
| id | uuid | PK |
| session_id | uuid | FK |
| message_id | uuid | FK |
| rewritten_query | text | Final retrieval query |
| top_k_initial | jsonb | Raw vector hits |
| top_k_reranked | jsonb | Reranked hits |
| retrieval_score_summary | jsonb | Stats |
| created_at | timestamptz | Audit |

#### `eval_runs`
Stores evaluation executions.

| Column | Type | Notes |
|---|---|---|
| id | uuid | PK |
| suite_name | text | smoke, retrieval_regression, full |
| commit_sha | text | Optional CI traceability |
| config | jsonb | Parameters |
| summary | jsonb | Aggregate metrics |
| created_at | timestamptz | Audit |

#### `eval_results`
Stores per-example evaluation output.

| Column | Type | Notes |
|---|---|---|
| id | uuid | PK |
| eval_run_id | uuid | FK |
| example_id | text | Stable golden ID |
| metric_name | text | precision_at_k, faithfulness, etc. |
| metric_value | numeric | Scalar score |
| result_payload | jsonb | Rich details |
| created_at | timestamptz | Audit |

## Supabase and pgvector design
Supabase is used for both the application database and the vector store, which matches the preferred stack in the test. Pgvector should be treated as one part of the retrieval pipeline rather than the whole retrieval strategy, because answer quality will depend heavily on chunk design, metadata, reranking, and eval loops, not just nearest-neighbor search.[file:1]

Recommended decisions:

- Use `ivfflat` or `hnsw` depending on the pgvector version and Supabase support level.
- Keep chunk embeddings and app data in the same Postgres cluster for simplicity.
- Create SQL functions for vector match queries so FastAPI stays clean.
- Store enough metadata to enable filter-first retrieval experiments later.
- Avoid overengineering ingestion queues in the initial implementation; a script plus job record is enough.

## Stripe Docs ingestion strategy
Stripe docs are broad, so the crawl scope should be constrained for the test version. A good submission scope is a curated subset such as payments, checkout, subscriptions, webhooks, and API authentication because those topics produce diverse but still manageable retrieval questions.[cite:1]

### Crawl rules
- Allow only canonical Stripe docs pages.
- Skip duplicate pages, search pages, changelog noise, and purely navigational pages.
- Prefer rendered content areas over global nav and footer text.
- Capture code examples only when they improve answerability; do not let long code blocks dominate chunk content.

### Chunking rules
Use a hierarchical chunker:

1. Split by page section headings.
2. Preserve heading path in metadata.
3. Merge small adjacent sections when below a token threshold.
4. Split oversized sections by paragraph boundaries.
5. Keep overlap modest, for example 50–100 tokens, to reduce citation ambiguity.

Recommended target: around 300–600 tokens per chunk for docs content, because this is usually large enough for explanation and small enough for accurate citation spans.

### Metadata fields per chunk
```json
{
  "product_area": "payments",
  "doc_type": "guide",
  "section_path": ["Payments", "Accept a payment", "Create a PaymentIntent"],
  "anchor": "create-a-paymentintent",
  "language": "en",
  "contains_code": true
}
```

## Embeddings and reranking
You asked to prefer open-source local embeddings and reranking for cost control. The blueprint should therefore formalize these interfaces so the project can start with local models and still swap later if needed.

### Recommended stack
- Embeddings: `bge-small-en-v1.5` or `e5-small-v2` for speed.
- Reranker: `bge-reranker-base` or a comparable cross-encoder.
- Optional lexical fallback: lightweight Postgres full-text search.

### Abstractions
Define contracts such as:

```python
class Embedder(Protocol):
    def embed_texts(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, query: str) -> list[float]: ...

class Reranker(Protocol):
    def rerank(self, query: str, candidates: list[RetrievedChunk]) -> list[RetrievedChunk]: ...
```

That lets the same retrieval pipeline support local, hosted, or hybrid models later.

## Option A agent architecture
The deeper part of the project should look like a Claude Managed Agent style system even if the first implementation uses a custom Python orchestration layer. The key is to show managed-agent thinking: explicit tools, stateful multi-turn control, strict grounding, and traceability.[file:1]

### Agent responsibilities
- Interpret user intent.
- Decide whether to call retrieval tools.
- Use session context for follow-up questions.
- Synthesize a grounded answer.
- Return citations in a predictable structure.
- Refuse unsupported claims when evidence is weak.

### Tool set to implement
The prompt says at least one custom tool; this plan implements all three suggested tools and makes them meaningful rather than decorative.[file:1]

#### `search_tool`
Purpose: retrieve candidate chunks from pgvector based on the normalized query and optional metadata filters.

Input:
```json
{
  "query": "How do I confirm a PaymentIntent?",
  "top_k": 8,
  "filters": {
    "product_area": "payments"
  }
}
```

Output:
```json
{
  "query_used": "how do i confirm a paymentintent",
  "results": [
    {
      "chunk_id": "uuid",
      "document_id": "uuid",
      "title": "Accept a payment",
      "url": "https://docs.stripe.com/...",
      "anchor": "confirm-the-paymentintent",
      "content": "...",
      "score": 0.83,
      "metadata": {}
    }
  ]
}
```

#### `source_ranker`
Purpose: rerank search results using a local cross-encoder and remove weak or redundant evidence.

Input:
```json
{
  "query": "How do I confirm a PaymentIntent?",
  "candidates": ["..."]
}
```

Output:
```json
{
  "ranked_results": [
    {
      "chunk_id": "uuid",
      "rerank_score": 0.94,
      "reason": "Directly explains confirmation flow"
    }
  ]
}
```

#### `citation_sourcer`
Purpose: convert ranked chunks into answer-ready citation objects, ideally with snippet spans and anchor links.

Input:
```json
{
  "ranked_chunk_ids": ["uuid1", "uuid2"],
  "max_citations": 3
}
```

Output:
```json
{
  "citations": [
    {
      "label": "Stripe Docs - Accept a payment",
      "url": "https://docs.stripe.com/...#confirm-the-paymentintent",
      "snippet": "Confirm the PaymentIntent to finalize the payment...",
      "section_path": "Payments > Accept a payment > Confirm the PaymentIntent"
    }
  ]
}
```

### Tool-calling sequence
The simplest robust loop is:

1. Agent receives user message.
2. Agent inspects session context.
3. Agent calls `search_tool`.
4. Agent calls `source_ranker`.
5. Agent calls `citation_sourcer`.
6. Agent synthesizes answer from ranked evidence only.
7. Agent stores message, traces, and retrieval event.

This fixed-order pipeline is acceptable for the test because it demonstrates deliberate architecture and keeps failure modes understandable.

### Session management
Persist sessions in Supabase to satisfy the “proper session management” expectation for Option A. Session state should include message history, latest user intent, retrieval query rewrites, tool traces, and final cited sources so the next turn can reason over prior grounding rather than just prior text.[file:1]

Recommended session strategy:

- `sessions` table for thread identity.
- `messages` table for conversation history.
- `tool_traces` for tool observability.
- `retrieval_events` for retrieval debugging.
- Windowed context assembly: include the last N turns plus a compact retrieval memory.

### Managed-agent prompt contract
The system prompt should enforce:

- Always prefer tool-grounded answers for factual Stripe docs questions.
- Do not answer from model memory when sources are missing.
- Cite every non-trivial factual claim.
- If the user asks a follow-up like “what about webhooks?”, rewrite query using session context before retrieval.
- If sources disagree or confidence is low, say so explicitly.

## FastAPI design
The FastAPI layer should prove engineering judgment rather than just basic routing. Endpoints should expose both recruiter-facing app behavior and operator-facing debugging capability.

### Endpoints

#### `POST /chat`
Primary endpoint for user Q&A.

Request:
```json
{
  "session_id": "optional-uuid",
  "message": "How do I confirm a PaymentIntent?",
  "top_k": 8,
  "max_citations": 3
}
```

Response:
```json
{
  "session_id": "uuid",
  "answer": "...",
  "citations": [
    {
      "label": "Stripe Docs - Accept a payment",
      "url": "https://docs.stripe.com/...",
      "snippet": "..."
    }
  ],
  "trace_id": "uuid",
  "latency_ms": 812
}
```

#### `POST /search`
Direct retrieval debug endpoint.

Use this to show reviewers the retrieval layer independently from generation. It is also useful for eval sanity checks.

#### `POST /ingest/run`
Triggers the selected docs ingestion job.

#### `GET /ingest/status/{job_id}`
Returns ingest progress, page counts, chunk counts, and failures.

#### `GET /sessions/{session_id}`
Returns session metadata.

#### `GET /sessions/{session_id}/messages`
Returns conversation history.

#### `POST /evals/run`
Runs the configured eval suite.

#### `GET /evals/latest`
Returns the latest eval summary and pass/fail gate result.

### Pydantic schemas
Use explicit request/response models for every endpoint. This is a simple but visible quality signal in a technical test because it improves API readability, validation, and generated docs.

## Retrieval architecture details
The retrieval path matters more than the LLM layer for RAG quality. A weak retrieval stack produces confident but incorrect answers with polished prose and bad citations.

### Retrieval pipeline stages
1. Normalize the raw user query.
2. Rewrite conversational follow-ups into standalone search queries.
3. Infer optional filters from session or query terms.
4. Retrieve top 20 vector candidates.
5. Apply metadata boosts and heuristic penalties.
6. Rerank top 10 with local cross-encoder.
7. Deduplicate near-identical chunks.
8. Select final 3–5 chunks for synthesis.
9. Build citation objects before answer generation.

### Good heuristic boosts
- Boost exact mention of Stripe object names like `PaymentIntent`, `Checkout Session`, `SetupIntent`, `Webhook endpoint`.
- Boost heading matches.
- Boost pages whose product area aligns with the query.
- Penalize chunks dominated by code if the question is conceptual.
- Penalize nav-like or glossary-like text.

### Confidence strategy
Create a simple retrieval confidence score using:

- top-1 vector similarity
- reranker margin between top results
- diversity across final sources
- presence of exact query terms in titles/headings

If confidence is below threshold:
- answer cautiously,
- cite available evidence,
- say the relevant page could not be confidently located,
- optionally recommend a narrower question.

## Citation design
Citations are not just UI decoration. They are part of the core trust model and directly required by the test.[file:1]

### Citation requirements
- Every answer should cite 1–3 sources when possible.
- Citations should point to canonical Stripe docs URLs.
- Prefer section anchors when available.
- Include short evidence snippets.
- Preserve ordering aligned with the answer narrative.

### Answer shape
```json
{
  "answer": "To confirm a PaymentIntent, create it, collect payment details, and confirm it on the client or server depending on your integration.",
  "citations": [
    {
      "label": "Stripe Docs - Accept a payment",
      "url": "https://docs.stripe.com/...#confirm-the-paymentintent",
      "snippet": "Confirm the PaymentIntent to finalize the payment..."
    }
  ]
}
```

### Citation assembly rules
- Do not cite chunks that were not used by the synthesis step.
- Avoid multiple citations to the same section unless each adds unique evidence.
- Keep snippets short and directly relevant.
- Track `used_chunk_ids` in the final answer trace for auditability.

## Evals architecture
This is the most important section of the blueprint because it turns the RAG app from “works on my machine” into an engineered system. The test explicitly says they care a lot about evaluation and want to see whether the RAG actually works, not just whether it runs.[file:1]

### Eval goals
The eval system should answer five questions:

1. Did retrieval find the right chunks?
2. Did reranking improve ordering?
3. Did the final answer stay faithful to sources?
4. Did the citations actually support the claims made?
5. Does quality regress when prompts, chunking, or models change?

### Eval dataset design
Create at least 10–15 high-quality QA examples because that is directly aligned with the test language. The best version is a small but intentionally diverse benchmark, not a random list of easy questions.[file:1]

#### Recommended eval categories
- Direct factual lookup.
- Multi-hop within one page.
- Multi-source synthesis across related Stripe pages.
- Ambiguous queries requiring disambiguation.
- Follow-up questions using session memory.
- Negative cases where docs do not clearly answer the question.
- Citation-sensitive cases where only one section is correct.

#### Example dataset schema
```json
{
  "id": "stripe_qa_001",
  "question": "What is a PaymentIntent used for?",
  "expected_answer_points": [
    "Tracks a payment lifecycle",
    "Handles authentication and payment state transitions"
  ],
  "gold_source_urls": [
    "https://docs.stripe.com/.../paymentintents"
  ],
  "gold_chunk_ids": ["uuid1", "uuid2"],
  "tags": ["payments", "factual_lookup"]
}
```

### Retrieval metrics
At minimum, track:

- Recall@k
- Precision@k
- MRR
- NDCG@k
- Hit rate on gold chunk IDs
- Hit rate on gold URLs

Why these matter:
- Recall@k tells whether the system can find relevant evidence at all.
- Precision@k shows how noisy top results are.
- MRR and NDCG expose ranking quality.
- Gold URL and chunk hit rates reveal whether citations can realistically be correct.

### Generation metrics
Use a mix of lightweight automated checks and LLM-as-judge:

- Faithfulness to cited sources.
- Answer correctness against gold answer points.
- Citation relevance.
- Completeness.
- Refusal quality for unsupported questions.

### LLM-as-judge design
For cost control, use a small number of judged examples per regression run and a fuller run on demand. The judge prompt should separately score:

- correctness
- groundedness
- citation support
- completeness
- concision

Store raw judge rationale for inspection, but use normalized numeric scores for gating.

### Heuristic checks that should exist even without a judge
These are cheap and should always run:

- Answer contains at least one citation for factual queries.
- Every citation URL exists in retrieved sources.
- No citation appears in the output if the source chunk was not retrieved.
- Unsupported-answer detector: flag answers with strong claims and zero evidence overlap.
- Snippet overlap check between answer claims and cited chunk text.

### Eval runners
Implement three runner types:

#### `retrieval_eval.py`
- loads retrieval goldens
- runs retrieval only
- computes ranking metrics
- outputs per-example failures

#### `generation_eval.py`
- runs full chat pipeline
- checks citation presence and structural validity
- computes heuristic quality metrics

#### `judge_eval.py`
- sends final answers plus sources to a judge model
- records scores and rationale

#### `regression_suite.py`
- combines all metrics
- compares against baseline thresholds
- exits non-zero in CI on regression

### Suggested CI gates
For a small test project, realistic initial gates might be:

- Recall@5 >= 0.80
- MRR >= 0.70
- Citation presence on factual queries >= 0.95
- Faithfulness judge average >= 4/5
- Unsupported claim rate <= 0.10

These thresholds are illustrative; the real point is to demonstrate that quality is being managed, not guessed.

### Failure analysis workflow
Every failed eval should be tagged with one primary failure reason:

- crawl miss
- chunking miss
- embedding miss
- reranker miss
- synthesis hallucination
- citation mismatch
- prompt issue
- session rewrite issue

This matters because RAG improvement depends on knowing *which layer* failed. Without this taxonomy, iteration becomes random.

### Eval-driven improvement loop
The architecture should explicitly support this cycle:

1. Run benchmark.
2. Inspect failed retrievals.
3. Adjust chunking, metadata, filters, or reranker.
4. Re-run retrieval metrics.
5. Inspect generation failures.
6. Tighten prompt or citation builder.
7. Re-run full suite.
8. Promote only if regression gates pass.

This loop is more important than any single model choice.

## Observability and traceability
To make the project debuggable, every `/chat` turn should log:

- raw user query
- rewritten query
- retrieved chunk IDs and scores
- reranked chunk IDs and scores
- final citation IDs
- answer latency
- model name
- token counts if available

A recruiter can then see that the system is not a black box. More importantly, this observability directly powers evals and failure analysis.

## AI coding assistant execution plan
Because the project will be built with AI coding assistants, the blueprint should define implementation slices that are small, testable, and hard to misunderstand.

### Phase 1: skeleton
- Bootstrap FastAPI app.
- Add config, health route, and Pydantic schemas.
- Set up Supabase connection and migrations.

### Phase 2: ingestion
- Implement Stripe crawler with limited scope.
- Parse and normalize docs content.
- Chunk content and upsert documents/chunks.

### Phase 3: retrieval
- Add embedding service and vector search.
- Add reranker abstraction and local reranker implementation.
- Expose `/search` endpoint.

### Phase 4: agent
- Implement session persistence.
- Add tool registry and the three tools.
- Implement `/chat` endpoint and answer synthesis.

### Phase 5: evals
- Seed 10–15 gold QA examples.
- Implement retrieval and generation eval runners.
- Add regression script and summary reporting.

### Phase 6: polish
- Improve README.
- Add architecture diagrams.
- Add Loom demo checkpoints.
- Document tradeoffs and next steps.

### AI-assistant prompting pattern
Each coding task should include:
- objective
- file(s) to edit
- input/output contract
- constraints
- acceptance tests

Example prompt for an AI coder:

```text
Implement app/retrieval/retriever.py.
Requirements:
- Accept query, top_k, optional filters.
- Use pgvector SQL function through the repository layer.
- Return RetrievedChunk objects.
- Do not perform reranking here.
- Include unit-testable pure functions for score normalization.
Acceptance:
- Empty query raises ValueError.
- Results preserve metadata and URL fields.
- No FastAPI imports.
```

## Concrete implementation notes

### FastAPI service boundaries
- Route handlers should be thin.
- Services orchestrate use cases.
- Repositories encapsulate SQL.
- Tools call services, not route handlers.
- Eval runners should exercise service layer APIs, not HTTP, except for one smoke test.

### Error handling
Create typed exceptions for:
- ingestion failure
- retrieval failure
- reranker unavailable
- citation assembly failure
- session not found
- eval dataset malformed

Map them to clean API responses.

### Security and operational basics
For the test, lightweight operational discipline is enough:
- environment-based secrets
- input validation on endpoints
- domain allowlist for crawler
- request timeouts
- structured logs
- no unsafe arbitrary URL ingestion in public API

## What to implement in 4–6 hours
The submitted vertical slice should be realistic for the timebox while still reflecting this blueprint.[file:1]

### Must-have
- limited Stripe docs ingestion
- Supabase + pgvector storage
- `/chat` and `/search`
- persistent sessions/messages/tool traces
- all three tools implemented in simple form
- citations in answers
- 10–15 eval examples
- retrieval metrics + one generation quality path

### Nice-to-have if time permits
- `/evals/run` endpoint
- metadata filters inferred from queries
- anchor-specific citations
- lexical fallback retrieval
- simple HTML or Swagger demo flow

### Explicitly defer
- distributed job queue
- advanced hybrid search tuning
- multi-lingual ingestion
- aggressive crawl freshness automation
- full production auth and rate limiting

## README structure recommendation
The repo README should mirror recruiter priorities from the test.

Suggested sections:
- problem statement
- architecture summary
- why Stripe docs
- why Option A
- stack choices and tradeoffs
- local setup
- ingest command
- run API
- run evals
- sample requests/responses
- evaluation methodology
- what would be built next with more time

## Tradeoffs to state clearly
A strong submission should openly explain tradeoffs:

- Limited crawl scope was chosen to maximize retrieval quality over breadth.
- Local embedding/reranking reduces cost but may underperform premium hosted models.
- The managed-agent architecture is represented through explicit tool orchestration and state persistence, even if the first version is not a full production Anthropic runtime.
- Evals are small but intentionally designed for regression testing rather than vanity demos.

## What to build next
The test explicitly asks what would be built next if this were day one of the job, so the architecture should reserve clear extension points.[file:1]

Recommended next steps:
- add hybrid retrieval with BM25/full-text + vector fusion
- improve chunking with heading-aware and code-aware variants
- build automatic crawl refresh jobs
- add judge model calibration and human-reviewed eval set growth
- add source coverage diagnostics per answer
- build a minimal reviewer UI for search, traces, and citations
- support streaming responses and partial tool events

## Final recommendation
The strongest version of this project is not the one with the most frameworks. It is the one that demonstrates disciplined system boundaries, thoughtful retrieval design, visible observability, and an evaluation loop that proves the RAG is improving over time.[file:1]

For this test, the architecture should make one thing unmistakable: the project was built by someone who understands that RAG quality is mostly a retrieval-and-evals engineering problem, and who can express that clearly in Python, APIs, and agent-tool design.
