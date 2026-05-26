"""Shared fixtures — synthetic 'sites' built in tmp_path."""
from __future__ import annotations

from pathlib import Path

import pytest


SAMPLE_INDEX = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Demo Site</title>
  <meta name="description" content="A small static site for testing.">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="canonical" href="https://example.com/">
  <meta property="og:title" content="Demo Site">
  <meta property="og:type" content="website">
  <link rel="stylesheet" href="css/styles.css">
</head>
<body>
  <a href="#main">Skip to main content</a>
  <header><nav><a href="about.html">About</a> <a href="missing.html">Missing</a></nav></header>
  <main id="main">
    <h1>Hello</h1>
    <h3>Sub</h3>
    <img src="logo.png" alt="Logo">
    <img src="hero.png">
    <form>
      <label for="name">Name</label>
      <input id="name" type="text">
      <input type="text" name="orphan">
    </form>
  </main>
  <footer>© 2026</footer>
  <script>alert('hi');</script>
</body>
</html>
"""

SAMPLE_ABOUT = """<!DOCTYPE html>
<html lang="en">
<head><title>About</title><meta name="viewport" content="width=device-width"></head>
<body>
  <main><h1>About</h1><p style="color:red">Welcome.</p></main>
</body>
</html>
"""


@pytest.fixture
def sample_site(tmp_path: Path) -> Path:
    """A two-page static site with a deliberate broken link (missing.html)."""
    (tmp_path / "index.html").write_text(SAMPLE_INDEX)
    (tmp_path / "about.html").write_text(SAMPLE_ABOUT)
    css = tmp_path / "css"
    css.mkdir()
    (css / "styles.css").write_text("body { font-family: sans-serif; }")
    return tmp_path


@pytest.fixture
def bootstrap_site(tmp_path: Path) -> Path:
    """A single-page site using Bootstrap from a CDN (framework + CDN detection)."""
    (tmp_path / "index.html").write_text("""<!DOCTYPE html>
<html lang="en">
<head>
  <title>Bootstrap demo</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
  <h1>BS</h1>
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
""")
    return tmp_path
