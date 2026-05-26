"""CLI smoke tests — argparse + run_contract_subcommands."""
import json
import subprocess
import sys
from pathlib import Path


def _run(*args) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "site_analyser.cli", *map(str, args)],
        capture_output=True,
        text=True,
    )


def test_cli_missing_target_nonzero(tmp_path: Path):
    r = _run(tmp_path / "nope")
    assert r.returncode != 0
    assert "Error" in r.stderr


def test_cli_dir_human_summary(sample_site: Path):
    r = _run(sample_site, "--no-external", "--no-broken-links")
    assert r.returncode == 0, r.stderr
    assert "Source:    dir" in r.stdout
    assert "Pages:" in r.stdout
    assert "Accessibility:" in r.stdout


def test_cli_dir_json(sample_site: Path):
    r = _run(sample_site, "--no-external", "--json")
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    assert data["source_kind"] == "dir"
    assert data["overall"]["page_count"] >= 2


def test_cli_manifest_subcommand():
    r = _run("manifest")
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    assert data["name"] == "site-analyser"
