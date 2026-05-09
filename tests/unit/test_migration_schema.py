from pathlib import Path


def test_init_migration_contains_pgvector_and_core_tables() -> None:
    migration_path = Path("app/db/migrations/001_init.sql")
    sql = migration_path.read_text(encoding="utf-8").lower()

    assert "create extension if not exists vector" in sql
    assert "create table if not exists documents" in sql
    assert "create table if not exists document_chunks" in sql
    assert "create table if not exists sessions" in sql
    assert "create table if not exists messages" in sql
    assert "create table if not exists tool_traces" in sql
    assert "create table if not exists retrieval_events" in sql
    assert "create table if not exists eval_runs" in sql
    assert "create table if not exists eval_results" in sql


def test_init_migration_defines_vector_match_function() -> None:
    migration_path = Path("app/db/migrations/001_init.sql")
    sql = migration_path.read_text(encoding="utf-8").lower()

    assert "create or replace function match_document_chunks" in sql
    assert "query_embedding vector(384)" in sql
    assert "order by dc.embedding <=> query_embedding" in sql
