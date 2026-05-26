"""Per-page signal extraction — BeautifulSoup + regex, all pure-Python.

Each function takes raw HTML (and sometimes the URL for context) and returns the
relevant pydantic sub-model. Kept side-effect-free so they're trivially testable
with inline HTML strings.
"""
from __future__ import annotations

import re
from typing import Iterable

from bs4 import BeautifulSoup

from .schemas import (
    AccessibilitySignals,
    InlineSignals,
    SEOSignals,
    StructureSignals,
    TechSignals,
    ValiditySignals,
)

# Framework detection — patterns ported from the ISYS3004 site-assessment
# pipeline (verbatim except for compile flags). Match real imports, not
# vanilla DOM calls (document.createElement is NOT React).
_FRAMEWORK_PATTERNS: dict[str, list[re.Pattern]] = {
    "bootstrap": [
        re.compile(r"bootstrap(?:\.min)?\.(css|js)", re.I),
        re.compile(r"""(?:src|href)=["'][^"']*bootstrap[^"']*["']""", re.I),
    ],
    "tailwind": [
        re.compile(r"tailwindcss|tailwind(?:\.min)?\.css", re.I),
        re.compile(r"""(?:src|href)=["'][^"']*tailwind[^"']*["']""", re.I),
    ],
    "bulma": [re.compile(r"bulma(?:\.min)?\.css", re.I)],
    "materialize": [re.compile(r"materialize(?:\.min)?\.(css|js)", re.I)],
    "react": [
        re.compile(r"""(?:src|href)=["'][^"']*react(?:\.min)?\.js[^"']*["']""", re.I),
        re.compile(r"reactDOM", re.I),
        re.compile(r"""from\s+['"]react['"]""", re.I),
        re.compile(r"React\.createElement\(", re.I),
    ],
    "vue": [
        re.compile(r"""(?:src|href)=["'][^"']*vue(?:\.min)?\.js[^"']*["']""", re.I),
        re.compile(r"new Vue\(", re.I),
        re.compile(r"""from\s+['"]vue['"]""", re.I),
    ],
    "angular": [
        re.compile(r"""(?:src|href)=["'][^"']*angular(?:\.min)?\.js[^"']*["']""", re.I),
        re.compile(r"ng-app|ng-controller", re.I),
    ],
    "jquery": [
        re.compile(r"""(?:src|href)=["'][^"']*jquery(?:\.min)?\.js[^"']*["']""", re.I),
        re.compile(r"\$\(document\)", re.I),
        re.compile(r"\bjQuery\b", re.I),
    ],
    "svelte": [re.compile(r"""from\s+['"]svelte['"]""", re.I)],
}

_CDN_PATTERN = re.compile(
    r"""(?:src|href)=["']https?://(?:cdn|unpkg|cdnjs|jsdelivr)[^"']*["']""",
    re.I,
)

# Inline-code regex (pre-bs4 raw scan — robust against malformed HTML).
_INLINE_STYLE_ATTR_RE = re.compile(r"""\sstyle=["'][^"']*["']""", re.I)
_STYLE_BLOCK_RE = re.compile(r"<style[\s>]", re.I)
_INLINE_SCRIPT_RE = re.compile(r"<script(?![^>]*\bsrc=)[^>]*>", re.I)
_EVENT_HANDLER_RE = re.compile(r"""\bon\w+=["'][^"']*["']""", re.I)


def parse(html: str) -> BeautifulSoup:
    """Single canonical entry point for parsing — `html.parser` (stdlib, no extra dep)."""
    return BeautifulSoup(html or "", "html.parser")


# ── Structure ─────────────────────────────────────────────────────────────


def structure(soup: BeautifulSoup) -> StructureSignals:
    """Semantic landmarks + heading hierarchy."""
    has_header = soup.find("header") is not None
    has_nav = soup.find("nav") is not None
    has_main = soup.find("main") is not None
    has_footer = soup.find("footer") is not None
    landmark_count = sum([has_header, has_nav, has_main, has_footer])

    heading_levels: list[int] = []
    for h in soup.find_all(re.compile(r"^h[1-6]$")):
        heading_levels.append(int(h.name[1]))

    skipped: list[str] = []
    for prev, cur in zip(heading_levels, heading_levels[1:]):
        if cur > prev + 1:
            skipped.append(f"h{prev}→h{cur}")

    return StructureSignals(
        has_header=has_header,
        has_nav=has_nav,
        has_main=has_main,
        has_footer=has_footer,
        semantic_landmark_count=landmark_count,
        h1_count=heading_levels.count(1),
        heading_levels=heading_levels,
        skipped_heading_levels=skipped,
        max_heading_depth=max(heading_levels) if heading_levels else 0,
    )


# ── Accessibility ─────────────────────────────────────────────────────────


def accessibility(soup: BeautifulSoup) -> AccessibilitySignals:
    """WCAG-flavoured heuristics."""
    images = soup.find_all("img")
    images_with_alt = [
        img for img in images if img.has_attr("alt") and (img["alt"] or img["alt"] == "")
    ]
    # alt="" is valid (decorative); presence of the attribute counts.
    images_alt_count = sum(1 for img in images if img.has_attr("alt"))

    inputs = soup.find_all(["input", "textarea", "select"])
    # Skip non-labelable inputs (hidden, submit, button, image).
    labelable = [
        i for i in inputs
        if (i.name != "input") or i.get("type", "text").lower() not in {"hidden", "submit", "button", "image", "reset"}
    ]
    with_label = 0
    for inp in labelable:
        # Either wrapped in a <label>, has aria-label/aria-labelledby, or has id matched by <label for=...>
        if inp.find_parent("label"):
            with_label += 1
            continue
        if inp.get("aria-label") or inp.get("aria-labelledby") or inp.get("title"):
            with_label += 1
            continue
        inp_id = inp.get("id")
        if inp_id and soup.find("label", attrs={"for": inp_id}):
            with_label += 1

    html_tag = soup.find("html")
    html_lang = bool(html_tag and html_tag.get("lang"))

    aria_count = sum(
        1
        for el in soup.find_all(True)
        for attr in el.attrs
        if attr.startswith("aria-") or attr == "role"
    )

    # Skip-link heuristic: first <a> whose href starts with '#' and text mentions
    # "skip" / "main content" / "navigation".
    skip_link = False
    for a in soup.find_all("a", href=True)[:3]:
        href = a.get("href", "")
        text = (a.get_text() or "").lower()
        if href.startswith("#") and ("skip" in text or "main" in text or "content" in text):
            skip_link = True
            break

    has_title = bool(soup.find("title") and soup.title.string and soup.title.string.strip())

    total_imgs = len(images)
    total_inputs = len(labelable)
    return AccessibilitySignals(
        images_total=total_imgs,
        images_with_alt=images_alt_count,
        alt_text_coverage=round(images_alt_count / total_imgs, 4) if total_imgs else 1.0,
        form_inputs_total=total_inputs,
        form_inputs_with_label=with_label,
        form_label_coverage=round(with_label / total_inputs, 4) if total_inputs else 1.0,
        html_lang_present=html_lang,
        aria_attribute_count=aria_count,
        skip_link_present=skip_link,
        has_title=has_title,
    )


# ── SEO ───────────────────────────────────────────────────────────────────


def seo(soup: BeautifulSoup) -> SEOSignals:
    title = None
    if soup.title and soup.title.string:
        title = soup.title.string.strip() or None

    meta_desc_tag = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
    meta_desc = meta_desc_tag.get("content", "").strip() if meta_desc_tag else None

    viewport_tag = soup.find("meta", attrs={"name": re.compile(r"^viewport$", re.I)})
    has_viewport = viewport_tag is not None

    canonical_tag = soup.find("link", attrs={"rel": lambda v: v and "canonical" in (v if isinstance(v, list) else [v])})
    canonical = canonical_tag.get("href") if canonical_tag else None

    og_tags = sorted({
        m.get("property", "")
        for m in soup.find_all("meta")
        if (m.get("property") or "").lower().startswith("og:")
    })

    return SEOSignals(
        title=title,
        title_length=len(title or ""),
        meta_description=meta_desc,
        meta_description_length=len(meta_desc or ""),
        has_viewport=has_viewport,
        canonical=canonical,
        open_graph_tags=og_tags,
    )


# ── Inline code (separation of concerns) ──────────────────────────────────


def inline(html: str) -> InlineSignals:
    """Raw-text regex scan — robust to malformed HTML and faster than re-parsing."""
    return InlineSignals(
        inline_style_attrs=len(_INLINE_STYLE_ATTR_RE.findall(html)),
        style_blocks=len(_STYLE_BLOCK_RE.findall(html)),
        inline_script_blocks=len(_INLINE_SCRIPT_RE.findall(html)),
        inline_event_handlers=len(_EVENT_HANDLER_RE.findall(html)),
    )


# ── Tech (frameworks / CDN) ───────────────────────────────────────────────


def tech(html: str) -> TechSignals:
    detected: list[str] = []
    for framework, patterns in _FRAMEWORK_PATTERNS.items():
        if any(p.search(html) for p in patterns):
            detected.append(framework)
    cdn_links = len(_CDN_PATTERN.findall(html))
    return TechSignals(frameworks_detected=sorted(detected), cdn_links=cdn_links)


# ── Validity (html5lib parse errors) ──────────────────────────────────────


def validity(html: str, sample_cap: int = 5) -> ValiditySignals:
    """Count and sample parse errors from html5lib's HTMLParser.

    html5lib reports parse errors via a callback on the tokenizer; we collect them
    via its `treebuilders` API directly to avoid heavyweight serialisation.
    """
    if not html:
        return ValiditySignals()
    try:
        from html5lib import HTMLParser
        from html5lib.treebuilders import getTreeBuilder
    except Exception as e:  # pragma: no cover — html5lib is a hard dep
        return ValiditySignals(parse_error_sample=[f"html5lib unavailable: {e}"])

    parser = HTMLParser(tree=getTreeBuilder("etree"))
    try:
        parser.parse(html)
    except Exception as e:
        return ValiditySignals(parse_error_sample=[f"html5lib parse failed: {e}"])
    errors = list(parser.errors)
    samples = []
    for _, code, _ in errors[:sample_cap]:
        samples.append(str(code))
    return ValiditySignals(parse_errors=len(errors), parse_error_sample=samples)


# ── Link discovery ────────────────────────────────────────────────────────


def discover_links(soup: BeautifulSoup, base_url: str) -> list[str]:
    """Return same-origin absolute URLs found in this page's <a href>.

    Skips fragments, mailto:, tel:, javascript:, and external origins.
    """
    from urllib.parse import urljoin, urlparse

    base_parsed = urlparse(base_url)
    out: list[str] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        absolute = urljoin(base_url, href)
        parsed = urlparse(absolute)
        if parsed.scheme not in ("http", "https"):
            continue
        if parsed.netloc != base_parsed.netloc:
            continue
        # Strip fragment so we don't visit the same page multiple times.
        cleaned = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if parsed.query:
            cleaned += f"?{parsed.query}"
        if cleaned not in seen:
            seen.add(cleaned)
            out.append(cleaned)
    return out


def discover_local_links(soup: BeautifulSoup, current_rel: str) -> list[str]:
    """For dir mode: same-page relative links → relative paths (no scheme).

    Returns the raw `href` of each same-page link so the dir crawler can resolve
    against the root directory. Skips fragments / mailto / tel / javascript / abs URLs.
    """
    from urllib.parse import urlparse

    out: list[str] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        parsed = urlparse(href)
        if parsed.scheme:
            continue  # absolute URL → external to the local site
        # Strip fragment
        clean = href.split("#", 1)[0]
        if not clean:
            continue
        if clean not in seen:
            seen.add(clean)
            out.append(clean)
    return out
