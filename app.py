from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from scout import cache
from scout.config import settings
from scout.pipeline import run
from scout.serp import BudgetExceeded, SerpError

STATIC = Path(__file__).parent / "static"
app = FastAPI(title="Internship Scout")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


class ScoutRequest(BaseModel):
    github: str = Field(min_length=1, max_length=39)
    query: str = Field(default="software engineer intern remote", max_length=120)
    location: str = Field(default="India", max_length=60)
    max_companies: int = Field(default=6, ge=1, le=10)
    with_news: bool = False


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/budget")
def budget():
    return {"this_month": cache.searches_this_month(), "budget": settings.monthly_budget,
            "key_configured": bool(settings.serpapi_key)}


@app.post("/api/scout")
def scout(req: ScoutRequest):
    try:
        return run(req.github.strip().lstrip("@"), req.query, req.location, req.max_companies, with_news=req.with_news)
    except BudgetExceeded as e:
        raise HTTPException(429, str(e))
    except SerpError as e:
        raise HTTPException(502, f"SerpApi: {e}")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(404, f"GitHub user '{req.github}' not found")
        raise HTTPException(502, f"GitHub API returned {e.response.status_code}; try again in a minute")
