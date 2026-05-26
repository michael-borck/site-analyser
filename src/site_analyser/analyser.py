"""SiteAnalyser — the orchestrator wiring fetcher + signals + external tools together."""
from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from . import signals as sig
from .exceptions import SiteAnalyserError
from .external import collect as collect_external
from .fetcher import FetchedPage, check_broken_links, crawl_url, walk_dir
from .schemas import (
    AccessibilitySignals,
    BrokenLink,
    InlineSignals,
    OverallSignals,
    PageAnalysis,
    PerfSignals,
    SiteAnalysis,
    ValiditySignals,
)


class SiteAnalyser:
    """Crawl a URL or walk a local dir, then extract site-quality signals."""

    def analyse(
        self,
        *,
        url: str | None = None,
        path: str | Path | None = None,
        max_pages: int = 10,
        check_broken: bool = True,
        external: bool = True,
    ) -> SiteAnalysis:
        if (url is None) == (path is None):
            raise SiteAnalyserError("Exactly one of `url` or `path` must be supplied")

        if url is not None:
            return self._analyse_url(
                url, max_pages=max_pages, check_broken=check_broken, external=external
            )
        return self._analyse_dir(
            Path(path), max_pages=max_pages, check_broken=check_broken, external=external
        )

    # ── URL mode ──────────────────────────────────────────────────────────

    def _analyse_url(
        self, url: str, *, max_pages: int, check_broken: bool, external: bool
    ) -> SiteAnalysis:
        pages_raw = crawl_url(url, max_pages=max_pages)
        pages = [_page_from_fetched(p, "url") for p in pages_raw]
        broken = self._broken_links_for_url(pages_raw, url) if check_broken else []
        ext = collect_external(url=url, html_files=None, css_files=None, enabled=external)
        return SiteAnalysis(
            source_kind="url",
            source=url,
            pages=pages,
            overall=_aggregate(pages, broken),
            external_tools=ext,
        )

    def _broken_links_for_url(self, fetched: list[FetchedPage], start_url: str) -> list[BrokenLink]:
        """Collect every internal link discovered on every page; HEAD-check them."""
        link_sources: dict[str, list[str]] = {}
        for page in fetched:
            if not page.html:
                continue
            soup = sig.parse(page.html)
            for link in sig.discover_links(soup, page.url):
                link_sources.setdefault(link, []).append(page.url)
        unique = list(link_sources.keys())
        results = check_broken_links(unique)
        broken: list[BrokenLink] = []
        for u, status, err in results:
            if err or (status is not None and status >= 400):
                broken.append(BrokenLink(
                    url=u, status=status, error=err, found_on=link_sources[u][:5]
                ))
        return broken

    # ── Dir mode ──────────────────────────────────────────────────────────

    def _analyse_dir(
        self, root: Path, *, max_pages: int, check_broken: bool, external: bool
    ) -> SiteAnalysis:
        pages_raw = walk_dir(root, max_pages=max_pages)
        pages = [_page_from_fetched(p, "dir") for p in pages_raw]
        broken = self._broken_links_for_dir(pages_raw, root) if check_broken else []

        html_files = sorted(
            p for p in root.rglob("*.html")
            if ".git" not in p.parts and "node_modules" not in p.parts
        )
        css_files = sorted(
            p for p in root.rglob("*.css")
            if ".git" not in p.parts and "node_modules" not in p.parts
        )
        ext = collect_external(
            url=None, html_files=html_files, css_files=css_files, enabled=external
        )
        return SiteAnalysis(
            source_kind="dir",
            source=str(root),
            pages=pages,
            overall=_aggregate(pages, broken),
            external_tools=ext,
        )

    def _broken_links_for_dir(self, fetched: list[FetchedPage], root: Path) -> list[BrokenLink]:
        """In dir mode, a 'broken link' is a relative href that doesn't resolve to a file."""
        from urllib.parse import urljoin

        broken: list[BrokenLink] = []
        existing_files: set[str] = set()
        for p in root.rglob("*"):
            if p.is_file():
                existing_files.add(str(p.relative_to(root)))

        for page in fetched:
            if not page.html:
                continue
            soup = sig.parse(page.html)
            for href in sig.discover_local_links(soup, page.url):
                # Same urljoin semantics as walk_dir — relative to the page, not to a dir.
                resolved = urljoin(page.url, href).replace("\\", "/").lstrip("./")
                # Treat directory-style links (no .html) as resolving to /index.html.
                check = resolved
                if not check.endswith(".html") and not Path(check).suffix:
                    check = (Path(check) / "index.html").as_posix()
                if check not in existing_files:
                    broken.append(BrokenLink(
                        url=resolved,
                        status=None,
                        error="file not found",
                        found_on=[page.url],
                    ))
        return broken


# ── Helpers ──────────────────────────────────────────────────────────────


def _page_from_fetched(p: FetchedPage, kind: str) -> PageAnalysis:
    """Run every per-page signal function on a fetched page."""
    if p.error or not p.html:
        return PageAnalysis(
            url=p.url,
            source_kind=kind,
            structure=sig.structure(sig.parse("")),
            accessibility=sig.accessibility(sig.parse("")),
            seo=sig.seo(sig.parse("")),
            inline=sig.inline(""),
            tech=sig.tech(""),
            validity=sig.validity(""),
            perf=PerfSignals(page_size_bytes=p.size_bytes, http_status=p.status),
            fetch_error=p.error or "no HTML content",
        )
    soup = sig.parse(p.html)
    seo_signals = sig.seo(soup)
    return PageAnalysis(
        url=p.url,
        source_kind=kind,
        title=seo_signals.title,
        structure=sig.structure(soup),
        accessibility=sig.accessibility(soup),
        seo=seo_signals,
        inline=sig.inline(p.html),
        tech=sig.tech(p.html),
        validity=sig.validity(p.html),
        perf=PerfSignals(page_size_bytes=p.size_bytes, http_status=p.status),
        fetch_error=None,
    )


def _aggregate(pages: list[PageAnalysis], broken: list[BrokenLink]) -> OverallSignals:
    """Roll per-page signals into a site-wide rollup."""
    if not pages:
        return OverallSignals(
            page_count=0,
            broken_links=broken,
            accessibility=AccessibilitySignals(),
            inline_totals=InlineSignals(),
            validity_totals=ValiditySignals(),
        )

    # Accessibility totals across all pages.
    imgs_total = sum(p.accessibility.images_total for p in pages)
    imgs_alt = sum(p.accessibility.images_with_alt for p in pages)
    inputs_total = sum(p.accessibility.form_inputs_total for p in pages)
    inputs_label = sum(p.accessibility.form_inputs_with_label for p in pages)
    aria_total = sum(p.accessibility.aria_attribute_count for p in pages)
    pages_with_lang = sum(1 for p in pages if p.accessibility.html_lang_present)
    pages_with_title = sum(1 for p in pages if p.accessibility.has_title)
    pages_with_skip = sum(1 for p in pages if p.accessibility.skip_link_present)

    acc_overall = AccessibilitySignals(
        images_total=imgs_total,
        images_with_alt=imgs_alt,
        alt_text_coverage=round(imgs_alt / imgs_total, 4) if imgs_total else 1.0,
        form_inputs_total=inputs_total,
        form_inputs_with_label=inputs_label,
        form_label_coverage=round(inputs_label / inputs_total, 4) if inputs_total else 1.0,
        html_lang_present=pages_with_lang == len(pages),
        aria_attribute_count=aria_total,
        skip_link_present=pages_with_skip > 0,
        has_title=pages_with_title == len(pages),
    )

    structure_summary = {
        "has_header": sum(1 for p in pages if p.structure.has_header),
        "has_nav": sum(1 for p in pages if p.structure.has_nav),
        "has_main": sum(1 for p in pages if p.structure.has_main),
        "has_footer": sum(1 for p in pages if p.structure.has_footer),
        "missing_h1": sum(1 for p in pages if p.structure.h1_count == 0),
        "skipped_levels": sum(1 for p in pages if p.structure.skipped_heading_levels),
    }
    seo_summary = {
        "has_title": sum(1 for p in pages if p.seo.title),
        "has_meta_description": sum(1 for p in pages if p.seo.meta_description),
        "has_viewport": sum(1 for p in pages if p.seo.has_viewport),
        "has_canonical": sum(1 for p in pages if p.seo.canonical),
        "has_og_tags": sum(1 for p in pages if p.seo.open_graph_tags),
    }

    frameworks: dict[str, list[str]] = {}
    for p in pages:
        for fw in p.tech.frameworks_detected:
            frameworks.setdefault(fw, []).append(p.url)

    inline_totals = InlineSignals(
        inline_style_attrs=sum(p.inline.inline_style_attrs for p in pages),
        style_blocks=sum(p.inline.style_blocks for p in pages),
        inline_script_blocks=sum(p.inline.inline_script_blocks for p in pages),
        inline_event_handlers=sum(p.inline.inline_event_handlers for p in pages),
    )

    validity_totals = ValiditySignals(
        parse_errors=sum(p.validity.parse_errors for p in pages),
        parse_error_sample=[
            s for p in pages for s in p.validity.parse_error_sample
        ][:10],
    )

    return OverallSignals(
        page_count=len(pages),
        broken_links=broken,
        accessibility=acc_overall,
        structure_summary=structure_summary,
        seo_summary=seo_summary,
        frameworks_detected=frameworks,
        cdn_link_total=sum(p.tech.cdn_links for p in pages),
        inline_totals=inline_totals,
        validity_totals=validity_totals,
        total_page_bytes=sum(p.perf.page_size_bytes for p in pages),
    )
