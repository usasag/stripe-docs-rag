"""Postgres-backed session manager.

Implements the same interface as ``InMemorySessionManager`` but persists
sessions and messages to Supabase/Postgres via the repository layer.
"""
from __future__ import annotations

from app.db.repositories import MessageRepository, SessionRepository


class PostgresSessionManager:
    def __init__(
        self,
        *,
        session_repo: SessionRepository,
        message_repo: MessageRepository,
    ) -> None:
        self.session_repo = session_repo
        self.message_repo = message_repo

    def ensure_session(self, session_id: str | None) -> str:
        if session_id:
            existing = self.session_repo.get_session(session_id)
            if existing is not None:
                return session_id
        return self.session_repo.create_session(session_id)

    def add_message(
        self,
        session_id: str,
        *,
        role: str,
        content: str,
        metadata: dict[str, object] | None = None,
    ) -> dict[str, object]:
        turn_index = self.message_repo.count_messages(session_id)
        model_name = (metadata or {}).get('model_name') if metadata else None
        msg_id = self.message_repo.insert_message(
            session_id=session_id,
            role=role,
            content=content,
            turn_index=turn_index,
            model_name=str(model_name) if model_name else None,
            metadata=metadata,
        )
        return {
            'id': msg_id,
            'role': role,
            'content': content,
            'turn_index': turn_index,
            'metadata': metadata or {},
        }

    def get_messages(self, session_id: str) -> list[dict[str, object]]:
        rows = self.message_repo.get_messages(session_id)
        return [
            {
                'role': r['role'],
                'content': r['content'],
                'turn_index': r['turn_index'],
                'metadata': r.get('metadata', {}),
            }
            for r in rows
        ]
