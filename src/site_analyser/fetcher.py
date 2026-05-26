"""Fetch HTML — either crawl a live URL or walk a local static-site directory.

Both modes produce a uniform list of (page_url, raw_html, http_status, byte_size).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import httpx

from .exceptions import SiteAnalyserError
from .signals import discover_links, discover_local_links, parse

DEFAULT_TIMEOUT = 15.0
DEFAULT_USER_AGENT = "site-analyser/0.1 (+https://github.com/michael-borck/site-analyser)"


@dataclass
class FetchedPage:
    url: str
    html: str
    status: int | None  # None in dir mode (no HTTP)
    size_bytes: int
    error: str | None = None


def crawl_url(
    start_url: str,
    *,
    max_pages: int = 10,
    timeout: float = DEFAULT_TIMEOUT,
) -> list[FetchedPage]:
    """Same-origin BFS crawl from `start_url`, capped at `max_pages` HTML pages."""
    parsed = urlparse(start_url)
    if parsed.scheme not in ("http", "https"):
        raise SiteAnalyserError(
            f"URL must use http(s) scheme: {start_url!r}"
        )

    visited: set[str] = set()
    pages: list[FetchedPage] = []
    frontier: list[str] = [start_url.rstrip("/")]

    with httpx.Client(
        follow_redirects=True,
        timeout=timeout,
        headers={"User-Agent": DEFAULT_USER_AGENT},
    ) as client:
        while frontier and len(pages) < max_pages:
            url = frontier.pop(0)
            if url in visited:
                continue
            visited.add(url)

            try:
                resp = client.get(url)
                content_type = resp.headers.get("content-type", "")
                if "html" not in content_type.lower():
                    # Still record the visit so it can show up as a (non-HTML) page;
                    # skip parsing/link-following.
                    pages.append(
                        FetchedPage(url=url, html="", status=resp.status_code, size_bytes=len(resp.content))
                    )
                    continue
                html = resp.text
                pages.append(
                    FetchedPage(url=url, html=html, status=resp.status_code, size_bytes=len(resp.content))
                )
                # Enqueue new internal links.
                soup = parse(html)
                for link in discover_links(soup, url):
                    if link not in visited and link not in frontier:
                        frontier.append(link)
            except httpx.HTTPError as e:
                pages.append(
                    FetchedPage(url=url, html="", status=None, size_bytes=0, error=str(e))
                )

    return pages


def walk_dir(
    root: Path,
    *,
    max_pages: int = 10,
) -> list[FetchedPage]:
    """Walk a local static-site directory, reading every reachable .html file.

    Uses index.html (if present at the root) as the entry point and follows
    same-tree relative links; otherwise enumerates all .html files (sorted).
    The `url` field is the path relative to `root` (e.g. 'index.html', 'about.html').
    """
    root = Path(root).resolve()
    if not root.is_dir():
        raise SiteAnalyserError(f"Path is not a directory: {root}")

    html_files = [
        p for p in sorted(root.rglob("*.html"))
        if ".git" not in p.parts and "node_modules" not in p.parts
    ]
    if not html_files:
        raise SiteAnalyserError(f"No .html files found under: {root}")

    by_rel = {str(p.relative_to(root)): p for p in html_files}

    # Prefer crawl ordering starting from index.html, then BFS via relative links;
    # if there's no index, fall back to the sorted file list.
    if "index.html" in by_rel:
        frontier: list[str] = ["index.html"]
        visited: set[str] = set()
        pages: list[FetchedPage] = []
        while frontier and len(pages) < max_pages:
            rel = frontier.pop(0)
            if rel in visited:
                continue
            visited.add(rel)
            abs_path = by_rel.get(rel)
            if not abs_path or not abs_path.exists():
                # Broken local link — record it.
                pages.append(
                    FetchedPage(url=rel, html="", status=None, size_bytes=0, error="file not found")
                )
                continue
            try:
                html = abs_path.read_text(errors="ignore")
            except Exception as e:
                pages.append(
                    FetchedPage(url=rel, html="", status=None, size_bytes=0, error=str(e))
                )
                continue
            pages.append(
                FetchedPage(url=rel, html=html, status=None, size_bytes=abs_path.stat().st_size)
            )
            soup = parse(html)
            for link in discover_local_links(soup, rel):
                # urljoin handles relative-to-page semantics correctly: from "index.html"
                # a link to "about.html" stays "about.html"; from "blog/post.html" it
                # becomes "blog/about.html". Don't append a trailing slash to `rel`
                # (that would treat the page itself as a directory).
                from urllib.parse import urljoin

                joined = urljoin(rel, link).replace("\\", "/").lstrip("./")
                if joined and joined not in visited and joined not in frontier:
                    frontier.append(joined)
        return pages

    # No index — analyse every file (capped).
    pages = []
    for p in html_files[:max_pages]:
        rel = str(p.relative_to(root))
        try:
            html = p.read_text(errors="ignore")
        except Exception as e:
            pages.append(FetchedPage(url=rel, html="", status=None, size_bytes=0, error=str(e)))
            continue
        pages.append(FetchedPage(url=rel, html=html, status=None, size_bytes=p.stat().st_size))
    return pages


def check_broken_links(
    urls: list[str],
    *,
    timeout: float = DEFAULT_TIMEOUT,
    cap: int = 50,
) -> list[tuple[str, int | None, str | None]]:
    """HEAD-check each URL (capped). Returns (url, status_or_None, error_or_None) tuples.

    Falls back to a small GET if HEAD returns 405. We don't follow redirects: a 301/302
    to a working page is fine; a final 4xx/5xx is what we care about.
    """
    out: list[tuple[str, int | None, str | None]] = []
    with httpx.Client(
        follow_redirects=True,
        timeout=timeout,
        headers={"User-Agent": DEFAULT_USER_AGENT},
    ) as client:
        for url in urls[:cap]:
            try:
                r = client.head(url)
                if r.status_code == 405:  # Method not allowed → try GET (just headers)
                    r = client.get(url)
                out.append((url, r.status_code, None))
            except httpx.HTTPError as e:
                out.append((url, None, str(e)))
    return out
