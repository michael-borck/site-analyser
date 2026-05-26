"""Tests for the local-directory walker (no network)."""
from pathlib import Path

import pytest

from site_analyser.exceptions import SiteAnalyserError
from site_analyser.fetcher import walk_dir


def test_walk_dir_with_index(sample_site: Path):
    pages = walk_dir(sample_site)
    urls = [p.url for p in pages]
    assert "index.html" in urls
    assert "about.html" in urls
    # missing.html is referenced but not present; still recorded as a broken page.
    assert any(p.error == "file not found" and p.url == "missing.html" for p in pages)


def test_walk_dir_missing_root(tmp_path: Path):
    with pytest.raises(SiteAnalyserError, match="not a directory"):
        walk_dir(tmp_path / "nope")


def test_walk_dir_no_html(tmp_path: Path):
    (tmp_path / "readme.txt").write_text("hi")
    with pytest.raises(SiteAnalyserError, match="No .html files"):
        walk_dir(tmp_path)


def test_walk_dir_max_pages(tmp_path: Path):
    # Many files, cap to 3.
    for i in range(5):
        (tmp_path / f"p{i}.html").write_text(f"<html><body>{i}</body></html>")
    pages = walk_dir(tmp_path, max_pages=3)
    assert len(pages) == 3


def test_walk_dir_ignores_node_modules(tmp_path: Path):
    (tmp_path / "index.html").write_text("<html><body></body></html>")
    nm = tmp_path / "node_modules" / "thing"
    nm.mkdir(parents=True)
    (nm / "junk.html").write_text("<html></html>")
    pages = walk_dir(tmp_path)
    assert all("node_modules" not in p.url for p in pages)
