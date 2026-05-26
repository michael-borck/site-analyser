"""FastAPI service — site-analyser.

Like git-analyser, /analyse takes a JSON body (not a multipart upload) — the
input is a URL or a directory path, not a file.
"""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from lens_contract import add_contract_routes, add_cors
from pydantic import BaseModel, model_validator

from .analyser import SiteAnalyser
from .exceptions import SiteAnalyserError
from .manifest import MANIFEST
from .schemas import SiteAnalysis

_lens = SiteAnalyser()

app = FastAPI(
    title="site-analyser",
    description="Site-quality signals for a deployed URL or a local static-site dir",
    version=MANIFEST["version"],
    docs_url="/docs",
    redoc_url="/redoc",
)

add_contract_routes(app, MANIFEST)
add_cors(app, env_prefix="SITE_ANALYSER")


class AnalyseRequest(BaseModel):
    url: str | None = None
    path: str | None = None
    max_pages: int = 10
    check_broken: bool = True
    external: bool = True

    @model_validator(mode="after")
    def _exactly_one(self):
        if (self.url is None) == (self.path is None):
            raise ValueError("Exactly one of `url` or `path` must be supplied")
        return self


@app.get("/")
async def root() -> dict[str, Any]:
    return {
        "service": "site-analyser",
        "version": MANIFEST["version"],
        "status": "running",
        "endpoints": {"health": "/health", "manifest": "/manifest", "analyse": "/analyse"},
    }


@app.post("/analyse", response_model=SiteAnalysis)
async def analyse(req: AnalyseRequest) -> SiteAnalysis:
    try:
        return _lens.analyse(
            url=req.url,
            path=req.path,
            max_pages=req.max_pages,
            check_broken=req.check_broken,
            external=req.external,
        )
    except SiteAnalyserError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
