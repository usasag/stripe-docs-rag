create extension if not exists vector;

create table if not exists documents (
    id uuid primary key,
    source_url text not null unique,
    source_domain text not null,
    title text,
    h1 text,
    breadcrumb jsonb default '[]'::jsonb,
    product_area text,
    content_hash text,
    raw_text text,
    metadata jsonb default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists document_chunks (
    id uuid primary key,
    document_id uuid not null references documents(id) on delete cascade,
    chunk_index int not null,
    section_path text,
    anchor text,
    content text not null,
    token_count int,
    embedding vector(384) not null,
    metadata jsonb default '{}'::jsonb,
    created_at timestamptz not null default now(),
    unique (document_id, chunk_index)
);

create table if not exists sessions (
    id uuid primary key,
    external_session_id text,
    user_label text,
    status text not null default 'active',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists messages (
    id uuid primary key,
    session_id uuid not null references sessions(id) on delete cascade,
    role text not null,
    content text not null,
    turn_index int not null,
    model_name text,
    metadata jsonb default '{}'::jsonb,
    created_at timestamptz not null default now(),
    unique (session_id, turn_index)
);

create table if not exists tool_traces (
    id uuid primary key,
    session_id uuid not null references sessions(id) on delete cascade,
    message_id uuid references messages(id) on delete set null,
    tool_name text not null,
    tool_input jsonb not null default '{}'::jsonb,
    tool_output jsonb not null default '{}'::jsonb,
    latency_ms int,
    success boolean not null default true,
    created_at timestamptz not null default now()
);

create table if not exists retrieval_events (
    id uuid primary key,
    session_id uuid not null references sessions(id) on delete cascade,
    message_id uuid references messages(id) on delete set null,
    rewritten_query text,
    top_k_initial jsonb default '[]'::jsonb,
    top_k_reranked jsonb default '[]'::jsonb,
    retrieval_score_summary jsonb default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists eval_runs (
    id uuid primary key,
    suite_name text not null,
    commit_sha text,
    config jsonb default '{}'::jsonb,
    summary jsonb default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists eval_results (
    id uuid primary key,
    eval_run_id uuid not null references eval_runs(id) on delete cascade,
    example_id text not null,
    metric_name text not null,
    metric_value numeric,
    result_payload jsonb default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create index if not exists idx_document_chunks_embedding
    on document_chunks using ivfflat (embedding vector_cosine_ops)
    with (lists = 100);

create index if not exists idx_documents_product_area on documents(product_area);
create index if not exists idx_chunks_document_id on document_chunks(document_id);
create index if not exists idx_messages_session_turn on messages(session_id, turn_index);
create index if not exists idx_tool_traces_session on tool_traces(session_id, created_at);
create index if not exists idx_retrieval_events_session on retrieval_events(session_id, created_at);
create index if not exists idx_eval_results_run on eval_results(eval_run_id);

create or replace function match_document_chunks(
    query_embedding vector(384),
    match_count int default 10,
    filters jsonb default '{}'::jsonb
)
returns table (
    chunk_id uuid,
    document_id uuid,
    source_url text,
    title text,
    section_path text,
    anchor text,
    content text,
    metadata jsonb,
    similarity float
)
language sql
stable
as $$
    select
        dc.id as chunk_id,
        dc.document_id,
        d.source_url,
        d.title,
        dc.section_path,
        dc.anchor,
        dc.content,
        dc.metadata,
        1 - (dc.embedding <=> query_embedding) as similarity
    from document_chunks dc
    join documents d on d.id = dc.document_id
    where (filters = '{}'::jsonb or dc.metadata @> filters)
    order by dc.embedding <=> query_embedding
    limit greatest(match_count, 1);
$$;
