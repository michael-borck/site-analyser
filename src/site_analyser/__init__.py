"""site-analyser — site-quality signals for a deployed URL or local static-site dir."""
from .analyser import SiteAnalyser
from .exceptions import SiteAnalyserError
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

__all__ = [
    "SiteAnalyser",
    "SiteAnalyserError",
    "SiteAnalysis",
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
