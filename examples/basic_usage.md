# Basic usage

Site-quality signals for a deployed URL or a local static-site directory — accessibility, structure, SEO, link health, framework detection, validity.

## Install

```bash
pip install site-analyser
```

## CLI

```bash
# Analyse a deployed site
site-analyser https://example.com

# Analyse a local build directory
site-analyser ./build

# Crawl more pages, skip external links, emit JSON
site-analyser https://example.com --max-pages 20 --no-external --json
```

## Python

```python
from site_analyser import SiteAnalyser

# A URL...
result = SiteAnalyser().analyse(url="https://example.com")

# ...or a local directory
# result = SiteAnalyser().analyse(path="./build")

print(result.overall.accessibility.alt_text_coverage)
```

## HTTP

```bash
site-analyser serve   # starts the API on port 8012

curl -H 'Content-Type: application/json' \
  -d '{"url": "https://example.com"}' \
  http://localhost:8012/analyse
```

Pass `{"path": "./build"}` instead of `url` to analyse a local directory (supply exactly one of `url` or `path`).
