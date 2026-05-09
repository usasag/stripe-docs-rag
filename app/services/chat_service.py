from __future__ import annotations


class ChatService:
    def __init__(self, *, runtime: object) -> None:
        self.runtime = runtime

    def chat(self, *, message: str, session_id: str | None, top_k: int = 8, max_citations: int = 3) -> dict[str, object]:
        return self.runtime.chat(message=message, session_id=session_id, top_k=top_k, max_citations=max_citations)
