"""Web search integration using DuckDuckGo."""

from __future__ import annotations

import logging
import re
from html import unescape

import httpx

logger = logging.getLogger(__name__)

DDG_URL = "https://html.duckduckgo.com/html/"
TIMEOUT = 10


async def search(query: str, max_results: int = 5) -> list[dict]:
    """Search DuckDuckGo and return parsed results.

    Returns a list of dicts with: title, url, snippet.
    """
    if not query.strip():
        return []

    try:
        async with httpx.AsyncClient(
            timeout=TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Ralph-Dashboard/1.0"},
        ) as client:
            resp = await client.post(DDG_URL, data={"q": query, "b": ""})
            resp.raise_for_status()
            return _parse_results(resp.text, max_results)
    except httpx.HTTPError as e:
        logger.warning("DuckDuckGo search failed: %s", e)
        return []
    except Exception as e:
        logger.warning("Search error: %s", e)
        return []


def _parse_results(html: str, max_results: int) -> list[dict]:
    """Parse DuckDuckGo HTML results page."""
    results = []

    # Match result blocks - DuckDuckGo lite uses <a class="result__a" href="...">title</a>
    # and <a class="result__snippet" ...>snippet</a>
    blocks = re.findall(
        r'class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>.*?'
        r'class="result__snippet"[^>]*>(.*?)</(?:a|span)',
        html, re.DOTALL
    )

    for url, title, snippet in blocks[:max_results]:
        # Clean HTML tags
        clean_title = _strip_tags(unescape(title)).strip()
        clean_snippet = _strip_tags(unescape(snippet)).strip()

        # DuckDuckGo wraps URLs in redirects, extract actual URL
        actual_url = _extract_url(url)

        if clean_title and actual_url:
            results.append({
                "title": clean_title,
                "url": actual_url,
                "snippet": clean_snippet,
            })

    # Fallback: try simpler pattern if above didn't match
    if not results:
        links = re.findall(
            r'<a[^>]*class="[^"]*result[^"]*"[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
            html, re.DOTALL
        )
        for url, title in links[:max_results]:
            clean_title = _strip_tags(unescape(title)).strip()
            actual_url = _extract_url(url)
            if clean_title and actual_url and actual_url.startswith("http"):
                results.append({
                    "title": clean_title,
                    "url": actual_url,
                    "snippet": "",
                })

    return results


def _strip_tags(text: str) -> str:
    """Remove HTML tags from text."""
    return re.sub(r"<[^>]+>", "", text)


def _extract_url(ddg_url: str) -> str:
    """Extract actual URL from DuckDuckGo redirect wrapper."""
    # DuckDuckGo wraps URLs like //duckduckgo.com/l/?uddg=https%3A%2F%2F...
    match = re.search(r"uddg=([^&]+)", ddg_url)
    if match:
        from urllib.parse import unquote
        return unquote(match.group(1))
    # Sometimes direct URLs
    if ddg_url.startswith("http"):
        return ddg_url
    if ddg_url.startswith("//"):
        return "https:" + ddg_url
    return ddg_url
