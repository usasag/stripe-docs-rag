"""
This file is a dependency injector for the FastAPI application.
It is the Composition root of the application.
It instantiates and wires all the dependencies together using lru_cache to cache dependencies.
This prevents memory leaks and redundant connection overhead.
Deps are layered in Infra, Data, Engine and Services.
If you want to add a new feature, you need to add it in the appropriate layer.
Example:
- If you want to add a new tool, you need to register it in the tool_registry_dep() function.
- If you want to add a new repository, you need to add it in the appropriate layer.
- If you want to add a new service, you need to add it in the appropriate layer.

"""

from __future__ import annotations

from functools import lru_cache

from app.agent.runtime import AgentRuntime
from app.agent.session_manager import InMemorySessionManager
from app.agent.tool_registry import ToolRegistry
from app.core.config import Settings, get_settings
from app.db.connection import ConnectionFactory
from app.db.postgres_store import PostgresIndexer, PostgresRetriever
from app.db.repositories import (
    EvalRunRepository,
    EvalResultRepository,
    IngestJobRepository,
    MessageRepository,
    RetrievalEventRepository,
    SessionRepository,
    ToolTraceRepository,
)
from app.ingestion.embedder import LocalHashEmbedder
from app.ingestion.indexer import InMemoryIndexer
from app.ingestion.ingest_service import IngestService
from app.retrieval.inmemory_retriever import InMemoryRetriever
from app.services.chat_service import ChatService
from app.services.eval_service import EvalService
from app.services.ingest_service import IngestOrchestrator
from app.services.search_service import SearchService
from app.services.session_service import SessionService
from app.tools.citation_sourcer import CitationSourcerTool
from app.tools.search_tool import SearchTool
from app.tools.source_ranker import SourceRankerTool


def settings_dep() -> Settings:
    return get_settings()


def db_enabled(settings: Settings) -> bool:
    return bool(settings.supabase_db_url and settings.supabase_db_url.strip())


# ---------------------------------------------------------------------------
# Connection factory (shared across all repos)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def connection_factory_dep() -> ConnectionFactory | None:
    settings = settings_dep()
    if not db_enabled(settings):
        return None
    return ConnectionFactory(db_url=settings.supabase_db_url or '')


# ---------------------------------------------------------------------------
# Repositories
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def session_repo_dep() -> SessionRepository | None:
    cf = connection_factory_dep()
    return SessionRepository(cf) if cf else None


@lru_cache(maxsize=1)
def message_repo_dep() -> MessageRepository | None:
    cf = connection_factory_dep()
    return MessageRepository(cf) if cf else None


@lru_cache(maxsize=1)
def trace_repo_dep() -> ToolTraceRepository | None:
    cf = connection_factory_dep()
    return ToolTraceRepository(cf) if cf else None


@lru_cache(maxsize=1)
def retrieval_event_repo_dep() -> RetrievalEventRepository | None:
    cf = connection_factory_dep()
    return RetrievalEventRepository(cf) if cf else None


@lru_cache(maxsize=1)
def eval_run_repo_dep() -> EvalRunRepository | None:
    cf = connection_factory_dep()
    return EvalRunRepository(cf) if cf else None


@lru_cache(maxsize=1)
def eval_result_repo_dep() -> EvalResultRepository | None:
    cf = connection_factory_dep()
    return EvalResultRepository(cf) if cf else None


@lru_cache(maxsize=1)
def ingest_job_repo_dep() -> IngestJobRepository | None:
    cf = connection_factory_dep()
    return IngestJobRepository(cf) if cf else None


# ---------------------------------------------------------------------------
# Embedder / Indexer / Retriever
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def embedder_dep() -> LocalHashEmbedder:
    return LocalHashEmbedder()


@lru_cache(maxsize=1)
def indexer_dep() -> InMemoryIndexer:
    return InMemoryIndexer()


@lru_cache(maxsize=1)
def postgres_indexer_dep() -> PostgresIndexer | None:
    settings = settings_dep()
    if not db_enabled(settings):
        return None
    return PostgresIndexer(db_url=settings.supabase_db_url or '')


@lru_cache(maxsize=1)
def retriever_dep() -> object:
    settings = settings_dep()
    if db_enabled(settings):
        return PostgresRetriever(db_url=settings.supabase_db_url or '', embedder=embedder_dep())
    return InMemoryRetriever(indexer=indexer_dep())


# ---------------------------------------------------------------------------
# Session manager (DB-backed when available)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def session_manager_dep() -> object:
    sr = session_repo_dep()
    mr = message_repo_dep()
    if sr is not None and mr is not None:
        from app.agent.postgres_session_manager import PostgresSessionManager
        return PostgresSessionManager(session_repo=sr, message_repo=mr)
    return InMemorySessionManager()


# ---------------------------------------------------------------------------
# Agent runtime
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def runtime_dep() -> AgentRuntime:
    chunk_cache = {}
    settings = settings_dep()

    registry = ToolRegistry()
    registry.register('search_tool', SearchTool(retriever=retriever_dep(), chunk_cache=chunk_cache))
    registry.register('source_ranker', SourceRankerTool(chunk_cache=chunk_cache))
    registry.register('citation_sourcer', CitationSourcerTool(chunk_lookup=lambda cid: chunk_cache.get(cid)))

    return AgentRuntime(
        session_manager=session_manager_dep(),
        tool_registry=registry,
        model_name=settings.model_name,
        trace_repo=trace_repo_dep(),
        retrieval_event_repo=retrieval_event_repo_dep(),
    )


# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def search_service_dep() -> SearchService:
    return SearchService(retriever=retriever_dep())


@lru_cache(maxsize=1)
def chat_service_dep() -> ChatService:
    return ChatService(runtime=runtime_dep())


@lru_cache(maxsize=1)
def session_service_dep() -> SessionService:
    return SessionService(session_manager=session_manager_dep())


@lru_cache(maxsize=1)
def ingest_service_dep() -> IngestOrchestrator:
    db_indexer = postgres_indexer_dep()
    job_repo = ingest_job_repo_dep()
    return IngestOrchestrator(
        ingest_service=IngestService(
            embedder=embedder_dep(),
            indexer=db_indexer if db_indexer is not None else indexer_dep(),
        ),
        job_repo=job_repo,
    )


@lru_cache(maxsize=1)
def eval_service_dep() -> EvalService:
    return EvalService(
        chat_service=chat_service_dep(),
        eval_run_repo=eval_run_repo_dep(),
        eval_result_repo=eval_result_repo_dep(),
    )
