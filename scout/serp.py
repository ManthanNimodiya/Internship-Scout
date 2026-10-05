"""Thin SerpApi client: Google Jobs, Google Search and Google News, all cached."""

import hashlib
import json

import httpx

from . import cache
from .config import settings

SERP_URL = "https://serpapi.com/search.json"


class SerpError(RuntimeError):
    pass


class BudgetExceeded(SerpError):
    pass


def search(engine: str, ttl_hours: float, **params) -> dict:
    key = hashlib.sha256(json.dumps({"engine": engine, **params}, sort_keys=True).encode()).hexdigest()
    hit = cache.get(key, ttl_hours)
    if hit is not None:
        return hit

    if not settings.serpapi_key:
        raise SerpError("SERPAPI_KEY is not set. Add it to .env (see .env.example).")
    if cache.searches_this_month() >= settings.monthly_budget:
        raise BudgetExceeded(
            f"Monthly search budget of {settings.monthly_budget} reached; cached results still work."
        )

    response = httpx.get(SERP_URL, params={"engine": engine, "api_key": settings.serpapi_key, **params}, timeout=40)
    cache.record_search(engine)
    data = response.json()
    if response.status_code != 200 or "error" in data:
        raise SerpError(data.get("error", f"SerpApi returned HTTP {response.status_code}"))

    data.pop("search_metadata", None)  # contains request ids; not worth keeping
    cache.put(key, data)
    return data


def jobs(query: str, location: str, pages: int = 1) -> list[dict]:
    """Google Jobs listings. One search per page of about 10 jobs."""
    results: list[dict] = []
    token = None
    for _ in range(pages):
        params = {"q": query, "location": location, "hl": "en"}
        if token:
            params["next_page_token"] = token
        data = search("google_jobs", ttl_hours=24, **params)
        results.extend(data.get("jobs_results", []))
        token = (data.get("serpapi_pagination") or {}).get("next_page_token")
        if not token:
            break
    return results


def google(query: str) -> dict:
    """Organic results plus the knowledge graph, which often carries the founding year and website."""
    return search("google", ttl_hours=24 * 14, q=query, hl="en", gl="us", num=10)


def news(query: str) -> list[dict]:
    return search("google_news", ttl_hours=24 * 3, q=query, hl="en", gl="us").get("news_results", [])
