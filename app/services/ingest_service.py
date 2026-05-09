"""
This file is a service for ingesting Stripe documentation.
It uses the crawler_service to crawl the Stripe documentation and the ingestion_service to process the crawled pages.

NON-NEGOTIABLE FEATURE
This is the entry point for the ingestion pipeline.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.ingestion.crawler import CrawledPage


class IngestJobStore:
    """Legacy in-memory job store. Kept for backward-compat with tests."""
    def __init__(self) -> None:
        self.jobs: dict[str, dict[str, object]] = {}


class IngestOrchestrator:
    def __init__(
        self,
        *,
        ingest_service: object,
        job_repo: Any | None = None,
        jobs: IngestJobStore | None = None,
    ) -> None:
        self.ingest_service = ingest_service
        self.job_repo = job_repo
        # Fallback to legacy in-memory store when no repo provided
        self._legacy_jobs = jobs or IngestJobStore()

    def _save_job(self, record: dict[str, object]) -> None:
        job_id = str(record['job_id'])
        if self.job_repo is not None:
            self.job_repo.insert_job(
                job_id=job_id,
                scope=str(record.get('scope', '')),
                status=str(record.get('status', 'completed')),
                stats={
                    'pages_seen': record.get('pages_seen', 0),
                    'documents_upserted': record.get('documents_upserted', 0),
                    'chunks_upserted': record.get('chunks_upserted', 0),
                },
            )
        else:
            self._legacy_jobs.jobs[job_id] = record

    def _get_job(self, job_id: str) -> dict[str, object] | None:
        if self.job_repo is not None:
            return self.job_repo.get_job(job_id)
        return self._legacy_jobs.jobs.get(job_id)

    def run(self, scope: str) -> dict[str, object]:
        job_id = str(uuid.uuid4())

        from app.ingestion.crawler_service import crawl_stripe_docs_sync
        from app.ingestion.crawler import CrawlConfig
        from app.core.config import get_settings

        settings = get_settings()
        
        # Determine seeds based on scope (for now we support 'payments' or fallback to a default)
        if scope == 'payments':
            seeds = ['https://docs.stripe.com/payments']
        else:
            seeds = ['https://docs.stripe.com']

        config = CrawlConfig(
            seeds=seeds,
            allowed_domains=['docs.stripe.com'],
            allowed_paths=['/payments', '/billing', '/webhooks', '/api', '/testing'],
        )

        pages, stats = crawl_stripe_docs_sync(
            config,
            max_pages=settings.crawler_max_pages,
            delay_ms=settings.crawler_delay_ms,
        )

        result = self.ingest_service.process_pages(pages)
        record = {
            'job_id': job_id,
            'status': 'completed',
            'scope': scope,
            'pages_seen': result.pages_seen,
            'documents_upserted': result.documents_upserted,
            'chunks_upserted': result.chunks_upserted,
        }
        self._save_job(record)
        return record

    def status(self, job_id: str) -> dict[str, object]:
        job = self._get_job(job_id)
        if job is not None:
            return job
        return {
            'job_id': job_id,
            'status': 'not_found',
            'pages_seen': 0,
            'documents_upserted': 0,
            'chunks_upserted': 0,
        }
