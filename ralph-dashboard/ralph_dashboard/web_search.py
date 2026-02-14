"""Web search integration using DuckDuckGo."""

from __future__ import annotations

import logging
import re
from html import unescape
from urllib.parse import unquote

import httpx

logger = logging.getLogger(__name__)

DDG_URL = "https://html.duckduckgo.com/html/"
TIMEOUT = 12


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
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) "
                    "Gecko/20100101 Firefox/120.0"
                ),
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
                "Referer": "https://html.duckduckgo.com/",
            },
        ) as client:
            resp = await client.post(DDG_URL, data={"q": query, "b": ""})
            resp.raise_for_status()
            html = resp.text
            results = _parse_results(html, max_results)
            if results:
                return results
            # Log the first 2000 chars for debugging if no results
            logger.debug("DDG HTML (first 2000): %s", html[:2000])
            return []
    except httpx.HTTPError as e:
        logger.warning("DuckDuckGo search failed: %s", e)
        return []
    except Exception as e:
        logger.warning("Search error: %s", e)
        return []


def _parse_results(html: str, max_results: int) -> list[dict]:
    """Parse DuckDuckGo HTML results page with multiple strategies."""
    results = []

    # Strategy 1: Match result__a + result__snippet (standard DDG lite HTML)
    blocks = re.findall(
        r'class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>'
        r'.*?'
        r'class="result__snippet"[^>]*>(.*?)</(?:a|span|td)',
        html, re.DOTALL
    )
    for url, title, snippet in blocks[:max_results]:
        _add_result(results, url, title, snippet)

    if len(results) >= max_results:
        return results[:max_results]

    # Strategy 2: Match result-link inside td elements
    if not results:
        blocks = re.findall(
            r'<a[^>]*rel="nofollow"[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
            html, re.DOTALL
        )
        snippets = re.findall(
            r'class="result__snippet"[^>]*>(.*?)</(?:a|span|td)',
            html, re.DOTALL
        )
        for i, (url, title) in enumerate(blocks[:max_results]):
            snippet = snippets[i] if i < len(snippets) else ""
            _add_result(results, url, title, snippet)

    if len(results) >= max_results:
        return results[:max_results]

    # Strategy 3: Broader match - any anchor with result class and href
    if not results:
        blocks = re.findall(
            r'<a[^>]*href="([^"]*)"[^>]*class="[^"]*result[^"]*"[^>]*>(.*?)</a>',
            html, re.DOTALL
        )
        if not blocks:
            # Try reversed order (class before href)
            blocks = re.findall(
                r'<a[^>]*class="[^"]*result[^"]*"[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
                html, re.DOTALL
            )
        for url, title in blocks[:max_results]:
            _add_result(results, url, title, "")

    if len(results) >= max_results:
        return results[:max_results]

    # Strategy 4: Extract links from result divs by web_result or result class
    if not results:
        result_divs = re.findall(
            r'<div[^>]*class="[^"]*(?:result|web-result)[^"]*"[^>]*>(.*?)</div>\s*</div>',
            html, re.DOTALL
        )
        for div in result_divs[:max_results]:
            link_match = re.search(r'href="([^"]*)"[^>]*>(.*?)</a>', div, re.DOTALL)
            if link_match:
                url, title = link_match.group(1), link_match.group(2)
                _add_result(results, url, title, "")

    return results[:max_results]


def _add_result(results: list[dict], raw_url: str, raw_title: str, raw_snippet: str) -> None:
    """Clean and add a single result to the list."""
    clean_title = _strip_tags(unescape(raw_title)).strip()
    clean_snippet = _strip_tags(unescape(raw_snippet)).strip()
    actual_url = _extract_url(raw_url)

    if clean_title and actual_url and actual_url.startswith("http"):
        # Avoid duplicate URLs
        if not any(r["url"] == actual_url for r in results):
            results.append({
                "title": clean_title,
                "url": actual_url,
                "snippet": clean_snippet,
            })


def _strip_tags(text: str) -> str:
    """Remove HTML tags from text."""
    return re.sub(r"<[^>]+>", "", text)


def _extract_url(ddg_url: str) -> str:
    """Extract actual URL from DuckDuckGo redirect wrapper."""
    # DuckDuckGo wraps URLs like //duckduckgo.com/l/?uddg=https%3A%2F%2F...
    match = re.search(r"uddg=([^&]+)", ddg_url)
    if match:
        return unquote(match.group(1))
    # Sometimes direct URLs
    if ddg_url.startswith("http"):
        return ddg_url
    if ddg_url.startswith("//"):
        return "https:" + ddg_url
    return ddg_url
