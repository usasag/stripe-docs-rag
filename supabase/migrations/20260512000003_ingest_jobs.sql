-- Migration 003: Ingest Jobs tracking

create table if not exists ingest_jobs (
    id varchar primary key,
    scope varchar not null,
    status varchar not null,
    pages_fetched int default 0,
    pages_failed int default 0,
    errors jsonb default '[]'::jsonb,
    created_at timestamp default now(),
    updated_at timestamp default now()
);
