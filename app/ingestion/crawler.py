from __future__ import annotations

from dataclasses import dataclass
from html import unescape
import re
from urllib.parse import urljoin, urlparse, urlunparse


@dataclass(frozen=True)
class CrawlConfig:
    seeds: list[str]
    allowed_domains: set[str]
    allowed_path_prefixes: tuple[str, ...]


@dataclass(frozen=True)
class CrawledPage:
    url: str
    html: str


_HREF_RE = re.compile(r"href=['\"]([^'\"]+)['\"]", re.IGNORECASE)


def _canonicalize_url(url: str) -> str:
    parsed = urlparse(url)
    clean = parsed._replace(fragment='', query='')
    return urlunparse(clean)


def is_allowed_url(url: str, config: CrawlConfig) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {'http', 'https'}:
        return False
    if parsed.netloc not in config.allowed_domains:
        return False
    if not config.allowed_path_prefixes:
        return True
    return any(parsed.path.startswith(prefix) for prefix in config.allowed_path_prefixes)


def extract_links(html: str, base_url: str, config: CrawlConfig) -> list[str]:
    seen: set[str] = set()
    results: list[str] = []

    for href in _HREF_RE.findall(html):
        candidate = _canonicalize_url(urljoin(base_url, unescape(href.strip())))
        if candidate in seen:
            continue
        if is_allowed_url(candidate, config):
            seen.add(candidate)
            results.append(candidate)

    return results
