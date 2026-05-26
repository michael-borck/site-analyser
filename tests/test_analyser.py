"""Integration tests — SiteAnalyser in dir mode end-to-end (no network)."""
from pathlib import Path

import pytest

from site_analyser import SiteAnalyser, SiteAnalyserError
from site_analyser.schemas import SiteAnalysis


def test_dir_mode_returns_site_analysis(sample_site: Path):
    r = SiteAnalyser().analyse(path=sample_site, external=False)
    assert isinstance(r, SiteAnalysis)
    assert r.source_kind == "dir"
    assert r.overall.page_count >= 2  # index + about (+ missing.html recorded as fetch_error)


def test_dir_mode_aggregates_signals(sample_site: Path):
    r = SiteAnalyser().analyse(path=sample_site, external=False)
    # SEO rollup
    assert r.overall.seo_summary["has_title"] >= 2
    assert r.overall.seo_summary["has_viewport"] >= 2
    assert r.overall.seo_summary["has_canonical"] >= 1
    assert r.overall.seo_summary["has_og_tags"] >= 1
    # Structure
    assert r.overall.structure_summary["has_main"] >= 2
    # Accessibility: 2 images, 1 with alt → 50% coverage on index.
    assert r.overall.accessibility.images_total >= 2
    # Inline: about.html has style="color:red"
    assert r.overall.inline_totals.inline_style_attrs >= 1


def test_dir_mode_broken_links(sample_site: Path):
    r = SiteAnalyser().analyse(path=sample_site, external=False)
    broken_urls = [b.url for b in r.overall.broken_links]
    assert "missing.html" in broken_urls


def test_dir_mode_framework_detected(bootstrap_site: Path):
    r = SiteAnalyser().analyse(path=bootstrap_site, external=False)
    assert "bootstrap" in r.overall.frameworks_detected
    assert r.overall.cdn_link_total >= 2  # CSS + JS CDN links


def test_neither_url_nor_path_raises():
    with pytest.raises(SiteAnalyserError, match="Exactly one"):
        SiteAnalyser().analyse(external=False)


def test_both_url_and_path_raises(sample_site: Path):
    with pytest.raises(SiteAnalyserError, match="Exactly one"):
        SiteAnalyser().analyse(url="https://example.com", path=sample_site, external=False)


def test_external_tools_skipped_when_disabled(sample_site: Path):
    r = SiteAnalyser().analyse(path=sample_site, external=False)
    e = r.external_tools
    assert e.lighthouse_available is False
    assert e.vnu_available is False
    assert e.lighthouse_scores is None
