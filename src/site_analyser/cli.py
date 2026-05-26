"""CLI entry point for site-analyser.

Usage:
  site-analyser https://example.com
  site-analyser ./build --json
  site-analyser https://example.com --max-pages 20 --no-external
  site-analyser serve
  site-analyser manifest
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse


def main() -> None:
    from lens_contract import run_contract_subcommands

    from .manifest import MANIFEST

    if run_contract_subcommands(
        MANIFEST,
        app_path="site_analyser.api:app",
        default_port=8012,
        env_prefix="SITE_ANALYSER",
    ):
        return

    parser = argparse.ArgumentParser(
        prog="site-analyser",
        description="Site-quality signals for a deployed URL or a local static-site directory",
        epilog="subcommands: `serve` (HTTP API on port 8012), `manifest` (capability manifest)",
    )
    parser.add_argument("target", help="URL (https://...) or local directory path")
    parser.add_argument("--max-pages", type=int, default=10, help="Max pages to crawl (default: 10)")
    parser.add_argument(
        "--no-broken-links", dest="check_broken", action="store_false",
        help="Skip the broken-link HEAD-check pass",
    )
    parser.add_argument(
        "--no-external", dest="external", action="store_false",
        help="Skip Lighthouse/vnu even if available",
    )
    parser.add_argument("--json", action="store_true", dest="as_json", help="Output raw JSON")
    args = parser.parse_args()

    _run(args)


def _run(args) -> None:
    from .analyser import SiteAnalyser
    from .exceptions import SiteAnalyserError

    parsed = urlparse(args.target)
    is_url = parsed.scheme in ("http", "https")

    try:
        if is_url:
            result = SiteAnalyser().analyse(
                url=args.target,
                max_pages=args.max_pages,
                check_broken=args.check_broken,
                external=args.external,
            )
        else:
            target_path = Path(args.target)
            if not target_path.exists():
                raise SiteAnalyserError(
                    f"Not a URL and not an existing path: {args.target}"
                )
            result = SiteAnalyser().analyse(
                path=target_path,
                max_pages=args.max_pages,
                check_broken=args.check_broken,
                external=args.external,
            )
    except SiteAnalyserError as e:
        if args.as_json:
            print(json.dumps({"error": str(e)}), file=sys.stderr)
        else:
            print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.as_json:
        print(result.model_dump_json(indent=2))
        return

    _print_summary(result)


def _print_summary(result) -> None:
    print(f"Source:    {result.source_kind}  {result.source}")
    o = result.overall
    print(f"Pages:     {o.page_count}  ({o.total_page_bytes:,} bytes total)")
    print()
    print("Structure:")
    print(f"  header={o.structure_summary.get('has_header',0)}/{o.page_count}  "
          f"nav={o.structure_summary.get('has_nav',0)}/{o.page_count}  "
          f"main={o.structure_summary.get('has_main',0)}/{o.page_count}  "
          f"footer={o.structure_summary.get('has_footer',0)}/{o.page_count}")
    if o.structure_summary.get("missing_h1"):
        print(f"  missing <h1> on {o.structure_summary['missing_h1']} page(s)")
    if o.structure_summary.get("skipped_levels"):
        print(f"  heading levels skipped on {o.structure_summary['skipped_levels']} page(s)")
    print()
    print("Accessibility:")
    a = o.accessibility
    print(f"  alt-text:    {a.images_with_alt}/{a.images_total}  ({a.alt_text_coverage:.0%} coverage)")
    print(f"  form labels: {a.form_inputs_with_label}/{a.form_inputs_total}  ({a.form_label_coverage:.0%} coverage)")
    print(f"  <html lang>: {'all pages' if a.html_lang_present else 'missing on some pages'}")
    print(f"  ARIA attrs:  {a.aria_attribute_count}")
    print(f"  skip-link:   {'present' if a.skip_link_present else 'absent'}")
    print()
    print("SEO:")
    print(f"  has-title:   {o.seo_summary.get('has_title',0)}/{o.page_count}")
    print(f"  meta-desc:   {o.seo_summary.get('has_meta_description',0)}/{o.page_count}")
    print(f"  viewport:    {o.seo_summary.get('has_viewport',0)}/{o.page_count}")
    print(f"  canonical:   {o.seo_summary.get('has_canonical',0)}/{o.page_count}")
    print(f"  open-graph:  {o.seo_summary.get('has_og_tags',0)}/{o.page_count}")
    print()
    if o.frameworks_detected:
        print(f"Frameworks:  {', '.join(o.frameworks_detected.keys())}")
    else:
        print("Frameworks:  none detected")
    if o.cdn_link_total:
        print(f"CDN links:   {o.cdn_link_total}")
    print()
    print("Inline-code totals:")
    i = o.inline_totals
    print(f"  style attrs={i.inline_style_attrs}  <style>={i.style_blocks}  "
          f"inline <script>={i.inline_script_blocks}  on*=handlers={i.inline_event_handlers}")
    print()
    print(f"Validity:    {o.validity_totals.parse_errors} HTML parse error(s)")
    if o.broken_links:
        print(f"Broken:      {len(o.broken_links)} link(s)")
        for bl in o.broken_links[:5]:
            status = f"HTTP {bl.status}" if bl.status else (bl.error or "?")
            print(f"             - {bl.url}  [{status}]")
    else:
        print("Broken:      none")
    e = result.external_tools
    print()
    print("External tools:")
    if e.lighthouse_scores:
        print(f"  Lighthouse: {e.lighthouse_scores}")
    elif e.lighthouse_available:
        print(f"  Lighthouse: available but failed — {e.lighthouse_error}")
    else:
        print("  Lighthouse: not available (install Node + run `npx lighthouse` for perf/a11y/SEO scores)")
    if e.vnu_html_errors is not None or e.vnu_css_errors is not None:
        print(f"  vnu HTML:   {e.vnu_html_errors} errors, {e.vnu_html_warnings} warnings")
        if e.vnu_css_errors is not None:
            print(f"  vnu CSS:    {e.vnu_css_errors} errors, {e.vnu_css_warnings} warnings")
    elif e.vnu_available:
        print(f"  vnu:        available but failed — {e.vnu_error}")
    else:
        print("  vnu:        not available (install Node + Java for deep HTML/CSS validation)")


if __name__ == "__main__":
    main()
