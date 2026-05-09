"""Shared database connection factory.

Provides a reusable connection factory that all repositories and store
classes share.  When ``psycopg`` is available and a *db_url* is supplied
the factory returns real Postgres connections; otherwise callers can
inject a ``connection_factory`` callable for testing.
"""
from __future__ import annotations

from typing import Any, Callable


class ConnectionFactory:
    """Thin wrapper around ``psycopg.connect`` and SQLModel engines."""

    def __init__(
        self,
        *,
        db_url: str = '',
        connection_factory: Callable[[], Any] | None = None,
    ) -> None:
        self.db_url = db_url
        self._factory = connection_factory
        self._engine = None

    def connect(self) -> Any:
        if self._factory is not None:
            return self._factory()
        if not self.db_url:
            raise RuntimeError('No db_url configured and no connection_factory provided')
        try:
            import psycopg  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise RuntimeError('psycopg is required when no connection_factory is provided') from exc
        return psycopg.connect(self.db_url)

    def get_engine(self) -> Any:
        """Get or create a SQLModel/SQLAlchemy engine."""
        if self._engine is not None:
            return self._engine
        
        if not self.db_url:
            raise RuntimeError('No db_url configured for engine creation')
            
        try:
            from sqlmodel import create_engine
        except ImportError as exc:
            raise RuntimeError('sqlmodel is required for get_engine') from exc
            
        # Ensure the URL uses psycopg3
        url = self.db_url
        if url.startswith('postgresql://'):
            url = url.replace('postgresql://', 'postgresql+psycopg://', 1)
        elif url.startswith('postgres://'):
            url = url.replace('postgres://', 'postgresql+psycopg://', 1)
            
        self._engine = create_engine(url)
        return self._engine

    def get_session(self) -> Any:
        """Get a new SQLModel Session."""
        try:
            from sqlmodel import Session
        except ImportError as exc:
            raise RuntimeError('sqlmodel is required for get_session') from exc
            
        return Session(self.get_engine())
