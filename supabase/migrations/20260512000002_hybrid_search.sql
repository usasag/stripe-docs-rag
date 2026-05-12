-- Migration 002: Add Hybrid Search (BM25 + pgvector via RRF)

-- 1. Add the generated tsvector column to support full-text search
alter table document_chunks
add column if not exists content_tsvector tsvector
generated always as (to_tsvector('english', coalesce(content, ''))) stored;

-- 2. Create a GIN index on the new column
create index if not exists idx_document_chunks_tsvector on document_chunks using gin (content_tsvector);

-- 3. Create the hybrid search function
create or replace function match_document_chunks_hybrid(
    query_text text,
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
    with semantic as (
        select dc.id, 
               1 - (dc.embedding <=> query_embedding) as sim,
               row_number() over (order by dc.embedding <=> query_embedding) as rank
        from document_chunks dc
        where (filters = '{}'::jsonb or dc.metadata @> filters)
        order by dc.embedding <=> query_embedding
        limit 100
    ),
    keyword as (
        select dc.id, 
               ts_rank(dc.content_tsvector, websearch_to_tsquery('english', query_text)) as ts_score,
               row_number() over (order by ts_rank(dc.content_tsvector, websearch_to_tsquery('english', query_text)) desc) as rank
        from document_chunks dc
        where (filters = '{}'::jsonb or dc.metadata @> filters) 
          and dc.content_tsvector @@ websearch_to_tsquery('english', query_text)
        order by ts_rank(dc.content_tsvector, websearch_to_tsquery('english', query_text)) desc
        limit 100
    ),
    combined as (
        select
            coalesce(s.id, k.id) as id,
            coalesce(1.0 / (60 + s.rank), 0.0) + coalesce(1.0 / (60 + k.rank), 0.0) as rrf_score
        from semantic s
        full outer join keyword k on s.id = k.id
    )
    select
        dc.id as chunk_id,
        dc.document_id,
        d.source_url,
        d.title,
        dc.section_path,
        dc.anchor,
        dc.content,
        dc.metadata,
        c.rrf_score as similarity
    from combined c
    join document_chunks dc on dc.id = c.id
    join documents d on d.id = dc.document_id
    order by c.rrf_score desc
    limit greatest(match_count, 1);
$$;
