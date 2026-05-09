"""Database repositories using SQLModel ORM.

Each repository encapsulates operations for a single table (or related group).
All use :class:`ConnectionFactory` to vend a `sqlmodel.Session`.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel, col, select

from app.db.connection import ConnectionFactory


# ---------------------------------------------------------------------------
# ORM Models
# ---------------------------------------------------------------------------

class DbSession(SQLModel, table=True):
    __tablename__ = "sessions"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    external_session_id: Optional[str] = None
    user_label: Optional[str] = None
    status: str = Field(default="active")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class DbMessage(SQLModel, table=True):
    __tablename__ = "messages"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    session_id: uuid.UUID
    role: str
    content: str
    turn_index: int
    model_name: Optional[str] = None
    # We use meta_data to avoid collision with SQLModel's internal metadata attribute
    meta_data: Dict[str, Any] = Field(default_factory=dict, sa_column=Column("metadata", JSONB))
    created_at: Optional[datetime] = None


class DbToolTrace(SQLModel, table=True):
    __tablename__ = "tool_traces"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    session_id: uuid.UUID
    message_id: Optional[uuid.UUID] = None
    tool_name: str
    tool_input: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSONB))
    tool_output: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSONB))
    latency_ms: Optional[int] = None
    success: bool = Field(default=True)
    created_at: Optional[datetime] = None


class DbRetrievalEvent(SQLModel, table=True):
    __tablename__ = "retrieval_events"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    session_id: uuid.UUID
    message_id: Optional[uuid.UUID] = None
    rewritten_query: Optional[str] = None
    top_k_initial: List[Any] = Field(default_factory=list, sa_column=Column(JSONB))
    top_k_reranked: List[Any] = Field(default_factory=list, sa_column=Column(JSONB))
    retrieval_score_summary: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSONB))
    created_at: Optional[datetime] = None


class DbEvalRun(SQLModel, table=True):
    __tablename__ = "eval_runs"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    suite_name: str
    commit_sha: Optional[str] = None
    config: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSONB))
    summary: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSONB))
    created_at: Optional[datetime] = None


class DbEvalResult(SQLModel, table=True):
    __tablename__ = "eval_results"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    eval_run_id: uuid.UUID
    example_id: str
    metric_name: str
    metric_value: Optional[float] = None
    result_payload: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSONB))
    created_at: Optional[datetime] = None


class DbIngestJob(SQLModel, table=True):
    __tablename__ = "ingest_jobs"
    id: str = Field(primary_key=True)
    scope: str
    status: str
    pages_fetched: int = Field(default=0)
    pages_failed: int = Field(default=0)
    errors: List[Dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSONB))
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Session repository
# ---------------------------------------------------------------------------

class SessionRepository:
    def __init__(self, cf: ConnectionFactory) -> None:
        self.cf = cf

    def create_session(self, session_id: str | None = None) -> str:
        sid = uuid.UUID(session_id) if session_id else uuid.uuid4()
        with self.cf.get_session() as session:
            # Check if exists to support "on conflict do nothing"
            existing = session.get(DbSession, sid)
            if not existing:
                db_session = DbSession(id=sid, status='active')
                session.add(db_session)
                session.commit()
        return str(sid)

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        with self.cf.get_session() as session:
            db_session = session.get(DbSession, uuid.UUID(session_id))
            if not db_session:
                return None
            return {
                'id': str(db_session.id),
                'external_session_id': db_session.external_session_id,
                'user_label': db_session.user_label,
                'status': db_session.status,
                'created_at': db_session.created_at,
                'updated_at': db_session.updated_at,
            }

    def update_status(self, session_id: str, status: str) -> None:
        with self.cf.get_session() as session:
            db_session = session.get(DbSession, uuid.UUID(session_id))
            if db_session:
                db_session.status = status
                session.add(db_session)
                session.commit()


# ---------------------------------------------------------------------------
# Message repository
# ---------------------------------------------------------------------------

class MessageRepository:
    def __init__(self, cf: ConnectionFactory) -> None:
        self.cf = cf

    def insert_message(
        self,
        *,
        session_id: str,
        role: str,
        content: str,
        turn_index: int,
        model_name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        msg_id = uuid.uuid4()
        with self.cf.get_session() as session:
            msg = DbMessage(
                id=msg_id,
                session_id=uuid.UUID(session_id),
                role=role,
                content=content,
                turn_index=turn_index,
                model_name=model_name,
                meta_data=metadata or {},
            )
            session.add(msg)
            session.commit()
        return str(msg_id)

    def get_messages(
        self,
        session_id: str,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        with self.cf.get_session() as session:
            statement = select(DbMessage).where(
                DbMessage.session_id == uuid.UUID(session_id)
            ).order_by(DbMessage.turn_index).offset(offset).limit(limit)
            
            rows = session.exec(statement).all()
            return [
                {
                    'id': str(r.id),
                    'role': r.role,
                    'content': r.content,
                    'turn_index': r.turn_index,
                    'model_name': r.model_name,
                    'metadata': r.meta_data,
                    'created_at': r.created_at,
                }
                for r in rows
            ]

    def count_messages(self, session_id: str) -> int:
        with self.cf.get_session() as session:
            # Using raw execute for count is more efficient, but let's stick to standard SQLModel query
            statement = select(DbMessage).where(DbMessage.session_id == uuid.UUID(session_id))
            return len(session.exec(statement).all())


# ---------------------------------------------------------------------------
# Tool trace repository
# ---------------------------------------------------------------------------

class ToolTraceRepository:
    def __init__(self, cf: ConnectionFactory) -> None:
        self.cf = cf

    def insert_trace(
        self,
        *,
        session_id: str,
        message_id: str | None = None,
        tool_name: str,
        tool_input: dict[str, Any],
        tool_output: dict[str, Any],
        latency_ms: int,
        success: bool = True,
    ) -> str:
        trace_id = uuid.uuid4()
        with self.cf.get_session() as session:
            trace = DbToolTrace(
                id=trace_id,
                session_id=uuid.UUID(session_id),
                message_id=uuid.UUID(message_id) if message_id else None,
                tool_name=tool_name,
                tool_input=tool_input,
                tool_output=tool_output,
                latency_ms=latency_ms,
                success=success,
            )
            session.add(trace)
            session.commit()
        return str(trace_id)

    def get_traces_for_session(self, session_id: str) -> list[dict[str, Any]]:
        with self.cf.get_session() as session:
            statement = select(DbToolTrace).where(
                DbToolTrace.session_id == uuid.UUID(session_id)
            ).order_by(DbToolTrace.created_at)
            
            rows = session.exec(statement).all()
            return [
                {
                    'id': str(r.id),
                    'message_id': str(r.message_id) if r.message_id else None,
                    'tool_name': r.tool_name,
                    'tool_input': r.tool_input,
                    'tool_output': r.tool_output,
                    'latency_ms': r.latency_ms,
                    'success': r.success,
                    'created_at': r.created_at,
                }
                for r in rows
            ]


# ---------------------------------------------------------------------------
# Retrieval event repository
# ---------------------------------------------------------------------------

class RetrievalEventRepository:
    def __init__(self, cf: ConnectionFactory) -> None:
        self.cf = cf

    def insert_event(
        self,
        *,
        session_id: str,
        message_id: str | None = None,
        rewritten_query: str,
        top_k_initial: list[dict[str, Any]],
        top_k_reranked: list[dict[str, Any]],
        retrieval_score_summary: dict[str, Any],
    ) -> str:
        event_id = uuid.uuid4()
        with self.cf.get_session() as session:
            event = DbRetrievalEvent(
                id=event_id,
                session_id=uuid.UUID(session_id),
                message_id=uuid.UUID(message_id) if message_id else None,
                rewritten_query=rewritten_query,
                top_k_initial=top_k_initial,
                top_k_reranked=top_k_reranked,
                retrieval_score_summary=retrieval_score_summary,
            )
            session.add(event)
            session.commit()
        return str(event_id)

    def get_events_for_session(self, session_id: str) -> list[dict[str, Any]]:
        with self.cf.get_session() as session:
            statement = select(DbRetrievalEvent).where(
                DbRetrievalEvent.session_id == uuid.UUID(session_id)
            ).order_by(DbRetrievalEvent.created_at)
            
            rows = session.exec(statement).all()
            return [
                {
                    'id': str(r.id),
                    'message_id': str(r.message_id) if r.message_id else None,
                    'rewritten_query': r.rewritten_query,
                    'top_k_initial': r.top_k_initial,
                    'top_k_reranked': r.top_k_reranked,
                    'retrieval_score_summary': r.retrieval_score_summary,
                    'created_at': r.created_at,
                }
                for r in rows
            ]


# ---------------------------------------------------------------------------
# Eval run repository
# ---------------------------------------------------------------------------

class EvalRunRepository:
    def __init__(self, cf: ConnectionFactory) -> None:
        self.cf = cf

    def insert_run(
        self,
        *,
        run_id: str,
        suite_name: str,
        config: dict[str, Any] | None = None,
        summary: dict[str, Any] | None = None,
    ) -> str:
        with self.cf.get_session() as session:
            run = DbEvalRun(
                id=uuid.UUID(run_id),
                suite_name=suite_name,
                config=config or {},
                summary=summary or {},
            )
            session.add(run)
            session.commit()
        return run_id

    def get_latest(self, suite_name: str | None = None) -> dict[str, Any] | None:
        with self.cf.get_session() as session:
            if suite_name:
                statement = select(DbEvalRun).where(
                    DbEvalRun.suite_name == suite_name
                ).order_by(col(DbEvalRun.created_at).desc()).limit(1)
            else:
                statement = select(DbEvalRun).order_by(col(DbEvalRun.created_at).desc()).limit(1)
                
            r = session.exec(statement).first()
            if not r:
                return None
            return {
                'id': str(r.id),
                'suite_name': r.suite_name,
                'config': r.config,
                'summary': r.summary,
                'created_at': r.created_at,
            }


# ---------------------------------------------------------------------------
# Eval result repository
# ---------------------------------------------------------------------------

class EvalResultRepository:
    def __init__(self, cf: ConnectionFactory) -> None:
        self.cf = cf

    def insert_results(self, eval_run_id: str, results: list[dict[str, Any]]) -> int:
        count = 0
        with self.cf.get_session() as session:
            for r in results:
                res = DbEvalResult(
                    id=uuid.uuid4(),
                    eval_run_id=uuid.UUID(eval_run_id),
                    example_id=str(r.get('example_id', '')),
                    metric_name=str(r.get('metric_name', '')),
                    metric_value=float(r.get('metric_value', 0.0)),
                    result_payload=r.get('result_payload', {}),
                )
                session.add(res)
                count += 1
            session.commit()
        return count

    def get_by_run(self, eval_run_id: str) -> list[dict[str, Any]]:
        with self.cf.get_session() as session:
            statement = select(DbEvalResult).where(
                DbEvalResult.eval_run_id == uuid.UUID(eval_run_id)
            ).order_by(DbEvalResult.created_at)
            
            rows = session.exec(statement).all()
            return [
                {
                    'id': str(r.id),
                    'example_id': r.example_id,
                    'metric_name': r.metric_name,
                    'metric_value': r.metric_value,
                    'result_payload': r.result_payload,
                    'created_at': r.created_at,
                }
                for r in rows
            ]


# ---------------------------------------------------------------------------
# Ingest job repository
# ---------------------------------------------------------------------------

class IngestJobRepository:
    """Ingest job tracking."""

    def __init__(self, cf: ConnectionFactory) -> None:
        self.cf = cf

    def insert_job(self, job_id: str, scope: str, status: str, stats: dict[str, Any]) -> None:
        with self.cf.get_session() as session:
            job = DbIngestJob(
                id=job_id,
                scope=scope,
                status=status,
                pages_fetched=stats.get('pages_fetched', 0),
                pages_failed=stats.get('pages_failed', 0),
                errors=stats.get('errors', []),
            )
            session.add(job)
            session.commit()

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self.cf.get_session() as session:
            job = session.get(DbIngestJob, job_id)
            if not job:
                return None
            return {
                'job_id': job.id,
                'scope': job.scope,
                'status': job.status,
                'pages_fetched': job.pages_fetched,
                'pages_failed': job.pages_failed,
                'errors': job.errors,
            }

    def update_status(self, job_id: str, status: str, stats: dict[str, Any] | None = None) -> None:
        with self.cf.get_session() as session:
            job = session.get(DbIngestJob, job_id)
            if job:
                job.status = status
                if stats:
                    job.pages_fetched = stats.get('pages_fetched', job.pages_fetched)
                    job.pages_failed = stats.get('pages_failed', job.pages_failed)
                    job.errors = stats.get('errors', job.errors)
                job.updated_at = datetime.utcnow()
                session.add(job)
                session.commit()
