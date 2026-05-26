"""Capability manifest for the lens family (consumed by auto-analyser)."""
from __future__ import annotations

from lens_contract import make_manifest

# Explicit-only: this member's input is a URL or a directory, not a single file
# whose extension implies the analysis. extensions=[] keeps it out of auto-routing
# (code-analyser claims .html/.css/.js for source-file analysis).
MANIFEST = make_manifest(
    name="site-analyser",
    accepts=["website", "url", "static-site"],
    extensions=[],
    auto_routable=False,
    produces="SiteAnalysis",
)
