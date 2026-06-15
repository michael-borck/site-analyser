"""Canonical public-surface test — the uniform family contract.

No network: only imports and metadata are exercised.
"""
import site_analyser
from site_analyser import (
    MANIFEST,
    SiteAnalyser,
    SiteAnalysis,
    __version__,
    analyse,
)


def test_canonical_names_import():
    assert SiteAnalyser is not None
    assert SiteAnalysis is not None
    assert MANIFEST is not None


def test_analyse_is_callable():
    assert callable(analyse)


def test_manifest_name():
    assert MANIFEST["name"] == "site-analyser"


def test_version_is_str():
    assert isinstance(__version__, str)


def test_names_in_all():
    for name in (
        "SiteAnalyser",
        "SiteAnalysis",
        "analyse",
        "MANIFEST",
        "__version__",
        "SiteAnalyserError",
    ):
        assert name in site_analyser.__all__
