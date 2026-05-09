"""Async HTTP crawler for Stripe documentation.

Uses httpx.AsyncClient with configurable concurrency and polite delays.
Respects ``CrawlConfig`` domain/path restrictions.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

import httpx

from app.ingestion.crawler import CrawlConfig, CrawledPage, extract_links, is_allowed_url

logger = logging.getLogger(__name__)


@dataclass
class CrawlStats:
    pages_fetched: int = 0
    pages_failed: int = 0
    errors: list[dict[str, str]] = field(default_factory=list)


async def crawl_stripe_docs(
    config: CrawlConfig,
    *,
    max_pages: int = 50,
    delay_ms: int = 500,
    timeout_s: float = 15.0,
) -> tuple[list[CrawledPage], CrawlStats]:
    """BFS crawl from seed URLs, respecting domain/path restrictions.

    Returns:
        Tuple of (crawled pages, crawl statistics).
    """
    visited: set[str] = set()
    queue: list[str] = list(config.seeds)
    pages: list[CrawledPage] = []
    stats = CrawlStats()

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(timeout_s),
        follow_redirects=True,
        headers={'User-Agent': 'StripeDocsRAGAgent/0.1'},
    ) as client:
        while queue and len(pages) < max_pages:
            url = queue.pop(0)
            if url in visited:
                continue
            visited.add(url)

            if not is_allowed_url(url, config):
                continue

            try:
                response = await client.get(url)
                response.raise_for_status()
                html = response.text

                pages.append(CrawledPage(url=url, html=html))
                stats.pages_fetched += 1
                logger.info('Crawled %s (%d/%d)', url, stats.pages_fetched, max_pages)

                # Extract and enqueue child links
                child_links = extract_links(html, url, config)
                for link in child_links:
                    if link not in visited:
                        queue.append(link)

            except Exception as exc:
                stats.pages_failed += 1
                stats.errors.append({'url': url, 'error': str(exc)})
                logger.warning('Failed to crawl %s: %s', url, exc)

            # Polite delay between requests
            if delay_ms > 0:
                await asyncio.sleep(delay_ms / 1000.0)

    return pages, stats


def crawl_stripe_docs_sync(
    config: CrawlConfig,
    *,
    max_pages: int = 50,
    delay_ms: int = 500,
    timeout_s: float = 15.0,
) -> tuple[list[CrawledPage], CrawlStats]:
    """Synchronous wrapper around the async crawler.

    Safe to call from synchronous contexts (e.g., FastAPI sync endpoints).
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're inside an existing event loop (e.g., FastAPI with uvicorn)
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(
                    asyncio.run,
                    crawl_stripe_docs(config, max_pages=max_pages, delay_ms=delay_ms, timeout_s=timeout_s),
                ).result()
    except RuntimeError:
        pass

    return asyncio.run(
        crawl_stripe_docs(config, max_pages=max_pages, delay_ms=delay_ms, timeout_s=timeout_s)
    )
