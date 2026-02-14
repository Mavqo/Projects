"""Web search integration using DuckDuckGo (free, no API key required).

Uses the 'ddgs' library (preferred) or 'duckduckgo-search' as fallback.
Both handle DuckDuckGo's anti-bot measures automatically.
Install: pip install ddgs
"""

from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)


async def search(query: str, max_results: int = 5) -> list[dict]:
    """Search DuckDuckGo and return parsed results.

    Runs in a thread executor since the search libraries are synchronous.

    Returns a list of dicts with: title, url, snippet.
    """
    if not query.strip():
        return []

    try:
        results = await asyncio.to_thread(_search_sync, query, max_results)
        return results
    except Exception as e:
        logger.warning("Search error: %s", e)
        return []


def _search_sync(query: str, max_results: int) -> list[dict]:
    """Synchronous DuckDuckGo search."""

    # Try ddgs package first (newer, actively maintained)
    try:
        from ddgs import DDGS

        with DDGS() as ddgs:
            raw_results = list(ddgs.text(query, max_results=max_results))
        results = _normalize_results(raw_results)
        if results:
            return results
    except ImportError:
        pass
    except Exception as e:
        logger.warning("ddgs search failed: %s", e)

    # Try duckduckgo-search package (older name)
    try:
        from duckduckgo_search import DDGS as OldDDGS

        with OldDDGS() as ddgs:
            raw_results = list(ddgs.text(query, max_results=max_results))
        results = _normalize_results(raw_results)
        if results:
            return results
    except ImportError:
        pass
    except Exception as e:
        logger.warning("duckduckgo-search failed: %s", e)

    # Final fallback: direct HTTP scrape
    return _fallback_scrape(query, max_results)


def _normalize_results(raw_results: list[dict]) -> list[dict]:
    """Normalize results from ddgs/duckduckgo-search libraries."""
    results = []
    for r in raw_results:
        title = r.get("title", "").strip()
        url = r.get("href", r.get("link", r.get("url", ""))).strip()
        snippet = r.get("body", r.get("snippet", r.get("description", ""))).strip()
        if title and url:
            results.append({"title": title, "url": url, "snippet": snippet})
    return results


def _fallback_scrape(query: str, max_results: int) -> list[dict]:
    """Fallback: scrape DuckDuckGo HTML lite page via httpx."""
    import re
    from html import unescape
    from urllib.parse import unquote

    try:
        import httpx
    except ImportError:
        logger.warning("httpx not installed for fallback search")
        return []

    try:
        resp = httpx.post(
            "https://html.duckduckgo.com/html/",
            data={"q": query, "b": ""},
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) "
                    "Gecko/20100101 Firefox/120.0"
                ),
            },
            timeout=10,
            follow_redirects=True,
        )
        resp.raise_for_status()
        html = resp.text
    except Exception as e:
        logger.warning("Fallback search HTTP failed: %s", e)
        return []

    results = []

    # Parse result__a links with result__snippet
    blocks = re.findall(
        r'class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
        html, re.DOTALL
    )
    snippets = re.findall(
        r'class="result__snippet"[^>]*>(.*?)</(?:a|span|td)',
        html, re.DOTALL
    )

    for i, (raw_url, raw_title) in enumerate(blocks[:max_results]):
        title = re.sub(r"<[^>]+>", "", unescape(raw_title)).strip()
        snippet = ""
        if i < len(snippets):
            snippet = re.sub(r"<[^>]+>", "", unescape(snippets[i])).strip()

        # Extract actual URL from DDG redirect
        match = re.search(r"uddg=([^&]+)", raw_url)
        url = unquote(match.group(1)) if match else raw_url
        if url.startswith("//"):
            url = "https:" + url

        if title and url.startswith("http"):
            results.append({"title": title, "url": url, "snippet": snippet})

    return results
