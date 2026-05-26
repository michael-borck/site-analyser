"""Pydantic schemas for site-analyser output."""
from __future__ import annotations

from pydantic import BaseModel, Field


class StructureSignals(BaseModel):
    """Semantic HTML + heading hierarchy for a single page."""

    has_header: bool = False
    has_nav: bool = False
    has_main: bool = False
    has_footer: bool = False
    semantic_landmark_count: int = 0
    h1_count: int = 0
    heading_levels: list[int] = Field(default_factory=list, description="Headings in DOM order (1–6).")
    skipped_heading_levels: list[str] = Field(
        default_factory=list,
        description="e.g. 'h1→h3' where an h2 was missing.",
    )
    max_heading_depth: int = 0


class AccessibilitySignals(BaseModel):
    """WCAG-flavoured heuristics derived from the parsed HTML."""

    images_total: int = 0
    images_with_alt: int = 0
    alt_text_coverage: float = Field(0.0, description="images_with_alt / images_total, 0–1.")
    form_inputs_total: int = 0
    form_inputs_with_label: int = 0
    form_label_coverage: float = Field(0.0, description="form_inputs_with_label / form_inputs_total, 0–1.")
    html_lang_present: bool = False
    aria_attribute_count: int = 0
    skip_link_present: bool = False
    has_title: bool = False


class SEOSignals(BaseModel):
    """Basic on-page SEO signals."""

    title: str | None = None
    title_length: int = 0
    meta_description: str | None = None
    meta_description_length: int = 0
    has_viewport: bool = False
    canonical: str | None = None
    open_graph_tags: list[str] = Field(default_factory=list, description="og:* property names present.")


class InlineSignals(BaseModel):
    """Separation-of-concerns smells — counts per page."""

    inline_style_attrs: int = 0
    style_blocks: int = 0
    inline_script_blocks: int = 0
    inline_event_handlers: int = 0


class TechSignals(BaseModel):
    """Front-end tech / dependency detection (regex-based, conservative)."""

    frameworks_detected: list[str] = Field(default_factory=list)
    cdn_links: int = 0


class ValiditySignals(BaseModel):
    """HTML well-formedness via html5lib parse errors (deep W3C via vnu when available)."""

    parse_errors: int = 0
    parse_error_sample: list[str] = Field(default_factory=list, description="First N error messages.")


class PerfSignals(BaseModel):
    """Lightweight perf hints (page weight + request).

    Real Lighthouse scores live under ExternalTools.lighthouse when available.
    """

    page_size_bytes: int = 0
    http_status: int | None = None


class PageAnalysis(BaseModel):
    """All per-page signals."""

    url: str = Field(description="Either the absolute URL (URL mode) or the path-as-URL (dir mode).")
    source_kind: str = Field(description="'url' or 'dir'.")
    title: str | None = None
    structure: StructureSignals
    accessibility: AccessibilitySignals
    seo: SEOSignals
    inline: InlineSignals
    tech: TechSignals
    validity: ValiditySignals
    perf: PerfSignals
    fetch_error: str | None = None


class BrokenLink(BaseModel):
    url: str
    status: int | None = None
    error: str | None = None
    found_on: list[str] = Field(default_factory=list)


class ExternalTools(BaseModel):
    """Outputs from optional external tools — None when not available/disabled."""

    lighthouse_available: bool = False
    lighthouse_scores: dict[str, int] | None = None
    lighthouse_error: str | None = None
    vnu_available: bool = False
    vnu_html_errors: int | None = None
    vnu_html_warnings: int | None = None
    vnu_css_errors: int | None = None
    vnu_css_warnings: int | None = None
    vnu_error: str | None = None


class OverallSignals(BaseModel):
    """Site-wide rollup of per-page signals."""

    page_count: int = 0
    broken_links: list[BrokenLink] = Field(default_factory=list)
    accessibility: AccessibilitySignals
    structure_summary: dict[str, int] = Field(
        default_factory=dict,
        description="Pages with each landmark: {'has_header': N, 'has_main': N, ...}",
    )
    seo_summary: dict[str, int] = Field(
        default_factory=dict,
        description="Pages satisfying each SEO check: {'has_title': N, 'has_viewport': N, ...}",
    )
    frameworks_detected: dict[str, list[str]] = Field(
        default_factory=dict,
        description="framework -> list of page URLs where it was detected.",
    )
    cdn_link_total: int = 0
    inline_totals: InlineSignals
    validity_totals: ValiditySignals
    total_page_bytes: int = 0


class SiteAnalysis(BaseModel):
    """Top-level result returned by SiteAnalyser.analyse()."""

    source_kind: str = Field(description="'url' or 'dir'.")
    source: str = Field(description="The URL or directory path supplied.")
    pages: list[PageAnalysis]
    overall: OverallSignals
    external_tools: ExternalTools
