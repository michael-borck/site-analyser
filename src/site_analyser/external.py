"""Optional external tools — Lighthouse + W3C vnu — gated by availability.

Both shell out via `npx` (Node) and degrade gracefully when not present. The
analyser surfaces availability + results inside the ExternalTools sub-model so
callers can tell the difference between "ran and found nothing" and "wasn't run
because the tool isn't installed".
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from .schemas import ExternalTools

_LIGHTHOUSE_CATEGORIES = ("accessibility", "performance", "seo", "best-practices")
_LIGHTHOUSE_TIMEOUT = 120  # seconds
_VNU_TIMEOUT = 90


def npx_available() -> bool:
    return shutil.which("npx") is not None


def run_lighthouse(url: str) -> dict[str, object]:
    """Run `npx lighthouse` against a URL; return parsed scores or an error dict."""
    if not npx_available():
        return {"available": False, "error": "npx not found on PATH"}

    try:
        result = subprocess.run(
            [
                "npx", "--yes", "lighthouse", url,
                "--output=json",
                "--chrome-flags=--headless --no-sandbox",
                f"--only-categories={','.join(_LIGHTHOUSE_CATEGORIES)}",
                "--quiet",
            ],
            capture_output=True, text=True, timeout=_LIGHTHOUSE_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return {"available": True, "error": "Lighthouse timed out"}
    except FileNotFoundError:
        return {"available": False, "error": "npx not found at call time"}

    if not result.stdout.strip():
        msg = (result.stderr or "Lighthouse produced no output").strip().splitlines()[-1]
        return {"available": True, "error": msg}
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        return {"available": True, "error": f"Could not parse Lighthouse output: {e}"}
    categories = data.get("categories") or {}
    scores: dict[str, int] = {}
    for cat_id, cat in categories.items():
        raw = cat.get("score")
        if raw is not None:
            scores[cat_id] = round(raw * 100)
    return {"available": True, "scores": scores}


def run_vnu(files: list[Path], *, css: bool = False) -> dict[str, object]:
    """Run `npx vnu-jar` against a list of files; return parsed error/warning counts."""
    if not files:
        return {"available": npx_available(), "errors": 0, "warnings": 0}
    if not npx_available():
        return {"available": False, "error": "npx not found on PATH"}

    cmd = ["npx", "--yes", "vnu-jar"]
    if css:
        cmd.append("--css")
    cmd.extend(["--format", "json", "--exit-zero-always"])
    cmd.extend(str(f) for f in files)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=_VNU_TIMEOUT)
    except subprocess.TimeoutExpired:
        return {"available": True, "error": "vnu timed out"}
    except FileNotFoundError:
        return {"available": False, "error": "npx not found at call time"}

    # vnu writes JSON on stderr.
    output = (result.stderr or "").strip()
    if not output:
        return {"available": True, "errors": 0, "warnings": 0}
    try:
        data = json.loads(output)
    except json.JSONDecodeError as e:
        return {"available": True, "error": f"Could not parse vnu output: {e}"}
    msgs = data.get("messages", []) or []
    errors = sum(1 for m in msgs if m.get("type") == "error")
    warnings = sum(1 for m in msgs if m.get("type") in ("warning", "non-document-error", "info"))
    return {"available": True, "errors": errors, "warnings": warnings}


def collect(
    *,
    url: str | None = None,
    html_files: list[Path] | None = None,
    css_files: list[Path] | None = None,
    enabled: bool = True,
) -> ExternalTools:
    """Run whichever optional tools are applicable and available.

    enabled=False short-circuits everything (used by `--no-external`).
    """
    if not enabled:
        return ExternalTools(lighthouse_available=False, vnu_available=False)

    npx = npx_available()

    out = ExternalTools(
        lighthouse_available=npx and url is not None,
        vnu_available=npx and bool((html_files or []) or (css_files or [])),
    )

    if url and npx:
        lh = run_lighthouse(url)
        if "scores" in lh:
            out.lighthouse_scores = lh["scores"]  # type: ignore[assignment]
        if "error" in lh:
            out.lighthouse_error = str(lh["error"])

    if html_files and npx:
        vh = run_vnu(html_files, css=False)
        if "errors" in vh:
            out.vnu_html_errors = vh["errors"]  # type: ignore[assignment]
            out.vnu_html_warnings = vh.get("warnings")  # type: ignore[assignment]
        if "error" in vh:
            out.vnu_error = (out.vnu_error or "") + str(vh["error"])

    if css_files and npx:
        vc = run_vnu(css_files, css=True)
        if "errors" in vc:
            out.vnu_css_errors = vc["errors"]  # type: ignore[assignment]
            out.vnu_css_warnings = vc.get("warnings")  # type: ignore[assignment]
        if "error" in vc:
            out.vnu_error = (out.vnu_error or "") + str(vc["error"])

    return out
