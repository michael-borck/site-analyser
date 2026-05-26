"""HTTP smoke tests — the family contract surface (JSON-body /analyse like git-analyser)."""
from pathlib import Path

from fastapi.testclient import TestClient

from site_analyser.api import app
from site_analyser.manifest import MANIFEST


client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["version"] == MANIFEST["version"]


def test_manifest():
    r = client.get("/manifest")
    assert r.status_code == 200
    m = r.json()
    assert m["name"] == "site-analyser"
    assert m["auto_routable"] is False


def test_root_lists_endpoints():
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body["service"] == "site-analyser"


def test_analyse_requires_exactly_one_of_url_or_path():
    r = client.post("/analyse", json={})
    assert r.status_code == 422  # pydantic validation

    r = client.post("/analyse", json={"url": "https://x", "path": "/tmp"})
    assert r.status_code == 422


def test_analyse_dir(sample_site: Path):
    r = client.post(
        "/analyse",
        json={"path": str(sample_site), "external": False, "check_broken": True},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["source_kind"] == "dir"
    assert body["overall"]["page_count"] >= 2
    # missing.html should surface as broken.
    broken_urls = [b["url"] for b in body["overall"]["broken_links"]]
    assert "missing.html" in broken_urls
