"""site-analyser — site-quality signals for a deployed URL or local static-site dir."""
from importlib.metadata import version as _v
from pathlib import Path

from .analyser import SiteAnalyser
from .exceptions import SiteAnalyserError
from .manifest import MANIFEST
from .schemas import (
    AccessibilitySignals,
    BrokenLink,
    ExternalTools,
    InlineSignals,
    OverallSignals,
    PageAnalysis,
    PerfSignals,
    SEOSignals,
    SiteAnalysis,
    StructureSignals,
    TechSignals,
    ValiditySignals,
)

__version__ = _v("site-analyser")
del _v


def analyse(
    *,
    url: str | None = None,
    path: str | Path | None = None,
    max_pages: int = 10,
    check_broken: bool = True,
    external: bool = True,
) -> SiteAnalysis:
    """Analyse a deployed URL or a local static-site directory.

    Exactly one of ``url`` or ``path`` must be supplied. Mirrors
    :meth:`SiteAnalyser.analyse`.
    """
    return SiteAnalyser().analyse(
        url=url,
        path=path,
        max_pages=max_pages,
        check_broken=check_broken,
        external=external,
    )


__all__ = [
    "SiteAnalyser",
    "SiteAnalysis",
    "analyse",
    "MANIFEST",
    "__version__",
    "SiteAnalyserError",
    "PageAnalysis",
    "OverallSignals",
    "AccessibilitySignals",
    "StructureSignals",
    "SEOSignals",
    "TechSignals",
    "InlineSignals",
    "ValiditySignals",
    "PerfSignals",
    "BrokenLink",
    "ExternalTools",
]
