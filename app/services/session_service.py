"""
This file is a service for managing chat sessions.
It uses the session_manager to get and store session information.

NON-NEGOTIABLE FEATURE
This is the entry point for the chat session management.
"""

from __future__ import annotations


class SessionService:
    def __init__(self, *, session_manager: object) -> None:
        self.session_manager = session_manager

    def get_session(self, session_id: str) -> dict[str, object]:
        """
        Get session information.
        """
        messages = self.session_manager.get_messages(session_id)
        if messages is None:
            messages = []
        return {
            'session_id': session_id,
            'message_count': len(messages),
            'status': 'active',
        }

    def get_messages(self, session_id: str) -> list[dict[str, object]]:
        """
        Get messages for a session.
        """
        return self.session_manager.get_messages(session_id)
