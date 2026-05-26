"""Unit tests for the per-page signal extractors (no I/O, no fetcher)."""
from site_analyser.signals import (
    accessibility,
    discover_links,
    discover_local_links,
    inline,
    parse,
    seo,
    structure,
    tech,
    validity,
)


class TestStructure:
    def test_landmarks_detected(self):
        html = "<html><body><header></header><nav></nav><main></main><footer></footer></body></html>"
        s = structure(parse(html))
        assert s.has_header and s.has_nav and s.has_main and s.has_footer
        assert s.semantic_landmark_count == 4

    def test_landmarks_missing(self):
        s = structure(parse("<html><body><div></div></body></html>"))
        assert s.semantic_landmark_count == 0
        assert not s.has_main

    def test_heading_hierarchy_with_skip(self):
        # h1 → h3 skips h2
        s = structure(parse("<html><body><h1>A</h1><h3>B</h3></body></html>"))
        assert s.heading_levels == [1, 3]
        assert s.h1_count == 1
        assert s.skipped_heading_levels == ["h1→h3"]

    def test_no_h1_flagged_via_count(self):
        s = structure(parse("<html><body><h2>Only</h2></body></html>"))
        assert s.h1_count == 0


class TestAccessibility:
    def test_alt_text_coverage(self):
        html = "<html><body><img alt='a'><img alt=''><img></body></html>"
        a = accessibility(parse(html))
        assert a.images_total == 3
        # alt='' counts as present (decorative is valid).
        assert a.images_with_alt == 2
        assert a.alt_text_coverage == round(2 / 3, 4)

    def test_form_label_coverage(self):
        html = """
        <form>
          <label for="a">A</label><input id="a">
          <label>Wrapped <input></label>
          <input aria-label="aria">
          <input>
          <input type="hidden">
        </form>
        """
        a = accessibility(parse(html))
        # Hidden input excluded; 4 labelable, 3 with label.
        assert a.form_inputs_total == 4
        assert a.form_inputs_with_label == 3

    def test_html_lang_and_title(self):
        a = accessibility(parse("<html lang='en'><head><title>T</title></head></html>"))
        assert a.html_lang_present
        assert a.has_title

    def test_skip_link(self):
        a = accessibility(parse("""
        <html><body>
        <a href="#main">Skip to main content</a>
        <main id="main"></main>
        </body></html>"""))
        assert a.skip_link_present


class TestSEO:
    def test_full_seo(self):
        html = """<html><head>
          <title>T</title>
          <meta name="description" content="d">
          <meta name="viewport" content="width=device-width">
          <link rel="canonical" href="https://x">
          <meta property="og:title" content="t">
          <meta property="og:type" content="website">
        </head></html>"""
        s = seo(parse(html))
        assert s.title == "T"
        assert s.meta_description == "d"
        assert s.has_viewport
        assert s.canonical == "https://x"
        assert set(s.open_graph_tags) == {"og:title", "og:type"}

    def test_empty_seo(self):
        s = seo(parse("<html><head></head></html>"))
        assert s.title is None
        assert s.meta_description is None
        assert not s.has_viewport


class TestInline:
    def test_counts(self):
        html = """
        <p style="color:red">x</p>
        <p style="color:blue">y</p>
        <style>a{}</style>
        <script>1</script>
        <script src="x.js"></script>
        <button onclick="f()">x</button>
        """
        i = inline(html)
        assert i.inline_style_attrs == 2
        assert i.style_blocks == 1
        # The <script src="x.js"> should NOT count as inline.
        assert i.inline_script_blocks == 1
        assert i.inline_event_handlers == 1


class TestTech:
    def test_bootstrap(self):
        html = '<link href="https://cdn.jsdelivr.net/npm/bootstrap@5/css/bootstrap.min.css">'
        t = tech(html)
        assert "bootstrap" in t.frameworks_detected
        assert t.cdn_links == 1

    def test_react_imports(self):
        html = "<script>import React from 'react'</script>"
        t = tech(html)
        assert "react" in t.frameworks_detected

    def test_no_false_positive_on_document_createelement(self):
        # The hard-won lesson from the ISYS3004 patterns.
        html = "<script>document.createElement('div')</script>"
        t = tech(html)
        assert "react" not in t.frameworks_detected


class TestValidity:
    def test_empty(self):
        v = validity("")
        assert v.parse_errors == 0

    def test_well_formed(self):
        v = validity("<!DOCTYPE html><html><body><p>ok</p></body></html>")
        assert v.parse_errors == 0

    def test_malformed_produces_errors(self):
        # Stray unclosed tags / unexpected end-of-file should produce parse errors.
        v = validity("<html><body><p>oops</body>")
        assert v.parse_errors > 0


class TestLinkDiscovery:
    def test_same_origin(self):
        html = """<html><body>
          <a href="/about">in</a>
          <a href="https://other.example/x">out</a>
          <a href="#section">frag</a>
          <a href="mailto:x@y.z">mail</a>
        </body></html>"""
        links = discover_links(parse(html), "https://example.com/")
        assert links == ["https://example.com/about"]

    def test_local_dir_links(self):
        html = '<a href="about.html">a</a><a href="https://x">x</a><a href="#z">z</a>'
        out = discover_local_links(parse(html), "index.html")
        assert out == ["about.html"]
