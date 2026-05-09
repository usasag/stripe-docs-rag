"""Database migration runner.

Reads all .sql files in the migrations directory and applies those
that haven't been applied yet, tracking state in the migrations.applied_migrations table.
"""
from __future__ import annotations

import logging
from pathlib import Path

from app.core.config import get_settings
from app.db.connection import ConnectionFactory

logger = logging.getLogger(__name__)


def run_migrations() -> None:
    """Run all pending database migrations."""
    settings = get_settings()
    if not settings.supabase_db_url:
        logger.info("No db_url configured; skipping migrations.")
        return

    logger.info("Initializing database schema migrations...")
    cf = ConnectionFactory(db_url=settings.supabase_db_url)

    # 1. Ensure migrations tracking table exists
    setup_sql = """
    create schema if not exists "migrations";
    set search_path to "migrations";

    create table if not exists "migrations".applied_migrations (
      id                            serial primary key,
      migration_name                varchar not null,
      created_at                    timestamp default now()
    );
    set search_path to "public";
    """

    with cf.connect() as conn:
        with conn.cursor() as cur:
            cur.execute(setup_sql)
        conn.commit()

        # 2. Get all available migration files
        migrations_dir = Path(__file__).parent / 'migrations'
        if not migrations_dir.exists():
            return
            
        sql_files = sorted([f for f in migrations_dir.iterdir() if f.name.endswith('.sql')])

        # 3. Apply missing migrations
        with conn.cursor() as cur:
            for sql_file in sql_files:
                migration_name = sql_file.name
                
                # Check if already applied
                cur.execute(
                    "select exists(select 1 from migrations.applied_migrations where migration_name = %s)",
                    (migration_name,)
                )
                if cur.fetchone()[0]:
                    continue

                logger.info("Applying migration: %s", migration_name)
                
                # Read and execute migration script
                script_content = sql_file.read_text(encoding='utf-8')
                try:
                    cur.execute(script_content)
                    
                    # Record it as applied
                    cur.execute(
                        "insert into migrations.applied_migrations (migration_name) values (%s)",
                        (migration_name,)
                    )
                    conn.commit()
                except Exception as exc:
                    conn.rollback()
                    logger.error("Failed to apply migration %s: %s", migration_name, exc)
                    raise
                    
    logger.info("Database schema is up to date.")
