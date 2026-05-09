from __future__ import annotations

import uuid


class InMemorySessionManager:
    def __init__(self) -> None:
        self.sessions: dict[str, list[dict[str, object]]] = {}

    def ensure_session(self, session_id: str | None) -> str:
        sid = session_id or str(uuid.uuid4())
        if sid not in self.sessions:
            self.sessions[sid] = []
        return sid

    def add_message(self, session_id: str, *, role: str, content: str, metadata: dict[str, object] | None = None) -> dict[str, object]:
        session = self.sessions.setdefault(session_id, [])
        record = {
            'role': role,
            'content': content,
            'turn_index': len(session),
            'metadata': metadata or {},
        }
        session.append(record)
        return record

    def get_messages(self, session_id: str) -> list[dict[str, object]]:
        return list(self.sessions.get(session_id, []))
