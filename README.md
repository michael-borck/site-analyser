# site-analyser

**Site-quality signals** for a deployed URL or a local static-site directory — the
[lens-family](https://github.com/michael-borck/lens-analysers) member that reads a *rendered/deployed*
website rather than its source files.

> `code-analyser` reads `.html`/`.css`/`.js` source files in isolation; this one crawls a site
> (live or local), parses each page, and returns accessibility / structure / SEO / link-health /
> framework / validity / perf signals. Pure-Python core (always pip-installable); optional
> [Lighthouse](https://github.com/GoogleChrome/lighthouse) and the
> [W3C Nu HTML Checker](https://validator.github.io/validator/) for deeper signals when those
> tools are on `PATH` (graceful degradation otherwise).

## Install

```bash
pip install site-analyser
```

Optional deeper signals (no Python install needed — `site-analyser` shells out if it finds them):

```bash
# Lighthouse (perf / a11y / SEO / best-practices scores) — needs Node + Chrome
npx -y lighthouse --version

# W3C Nu HTML Checker (deep HTML/CSS validation) — needs Node + Java
npx -y vnu-jar --help
```

## Use

**Python:**

```python
from site_analyser import SiteAnalyser

result = SiteAnalyser().analyse(url="https://example.com")          # live URL
result = SiteAnalyser().analyse(path="./build")                     # local static-site dir
print(result.overall.page_count)                                    # 12
print(result.overall.accessibility.alt_text_coverage)               # 0.94
print(result.overall.broken_links)                                  # []
print(result.overall.frameworks_detected)                           # {'bootstrap': ['/index.html']}
```

**CLI:**

```bash
site-analyser https://example.com                # human summary
site-analyser ./build --json                     # raw JSON of a local dir
site-analyser https://example.com --max-pages 20
site-analyser ./build --no-external              # skip Lighthouse/vnu even if available
site-analyser serve                              # HTTP API on port 8012
site-analyser manifest                           # capability manifest
```

**HTTP** (`site-analyser serve` on port 8012):

```bash
curl -X POST http://localhost:8012/analyse \
  -H 'content-type: application/json' \
  -d '{"url": "https://example.com", "max_pages": 10}'

curl http://localhost:8012/health
curl http://localhost:8012/manifest
```

Like `git-analyser`, the API takes a **JSON body** (not a multipart upload) — exactly one of
`url` or `path` must be set.

## Signals

Per page and rolled up across the site:

- **Crawl** — internal-link discovery, page count, **broken links** (internal HEAD checks).
- **Structure** — semantic HTML (`<header>`/`<nav>`/`<main>`/`<footer>`), heading hierarchy
  (missing `<h1>`, skipped levels, depth).
- **Accessibility (WCAG heuristics)** — alt-text coverage, form-label coverage, `lang` on `<html>`,
  ARIA usage, skip-link, image count, doc-language coverage.
- **SEO** — `<title>`, meta description, viewport, canonical, OpenGraph coverage.
- **Tech** — framework detection (Bootstrap, Tailwind, Bulma, Materialize, React, Vue, Angular,
  jQuery, Svelte), CDN-link detection, inline `style=` / `<style>` / `<script>` / `on*=` counts.
- **Validity** — HTML parse-error count (html5lib); deep W3C via `vnu` if present.
- **Perf** — page weight (bytes), HTTP status (URL mode); real Lighthouse scores if present.
- **External tools (when on `PATH`)** — Lighthouse categories (perf/a11y/SEO/best-practices),
  `vnu` HTML/CSS error/warning counts. Absence is reported (not an error).

## The family

Part of the [lens analyser family](https://github.com/michael-borck/lens-analysers).

| What you want | Use |
|---|---|
| Source-file metrics on `.html`/`.css`/`.js` | **code-analyser** |
| The rendered/deployed site (URL or build dir) | **site-analyser** (this) |
| Source-history process signals | **git-analyser** |
| Any file → right engine | **auto-analyser** |

## Limits

- Pure-Python a11y/perf signals are heuristics — Lighthouse remains the gold standard for the
  full picture. Install it (`npx lighthouse --version` works) for the deep numbers.
- The crawler follows same-origin links only, up to `max_pages` (default 10).
- Broken-link checking does internal HEAD requests; external links are not fetched by default.
- v1 doesn't handle JS-rendered content — pages are parsed from the raw HTML response.

## License

MIT
