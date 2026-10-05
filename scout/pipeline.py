"""Profile → search → check companies → rank → draft. Search spend is capped by max_companies."""

from dataclasses import asdict

from . import cache, serp
from .companies import enrich
from .config import settings
from .drafts import draft, mailto
from .github import profile as build_profile
from .rank import score


def run(github_user: str, query: str, location: str = "India", max_companies: int = 6, pages: int = 1,
        with_news: bool = False) -> dict:
    before = cache.searches_this_month()
    prof = build_profile(github_user)
    listings = serp.jobs(query, location, pages=pages)

    # One listing per company: the one that scores best before any extra searches are spent.
    best: dict[str, tuple[float, dict]] = {}
    for job in listings:
        name = (job.get("company_name") or "").strip()
        if not name:
            continue
        s, _, _ = score(job, None, prof)
        if name not in best or s > best[name][0]:
            best[name] = (s, job)
    shortlist = sorted(best.items(), key=lambda kv: -kv[1][0])[:max_companies]

    results = []
    for name, (_, job) in shortlist:
        company = enrich(name, with_news=with_news)
        points, reasons, overlap = score(job, company, prof)
        email = draft(prof, name, job.get("title", ""), overlap, f"{job.get('title', '')} {job.get('description', '')}")
        apply = [{"title": o.get("title"), "link": o.get("link")} for o in job.get("apply_options", [])[:3]]
        results.append({
            "score": points,
            "reasons": reasons,
            "job": {
                "title": job.get("title"),
                "location": job.get("location"),
                "via": job.get("via"),
                "posted": (job.get("detected_extensions") or {}).get("posted_at"),
                "apply": apply,
            },
            "company": asdict(company),
            "draft": {**email, "mailto": mailto(company.email, email["subject"], email["body"]) if company.email else ""},
        })
    results.sort(key=lambda r: -r["score"])

    return {
        "profile": {
            "username": prof.username,
            "name": prof.name,
            "total_merged": prof.total_merged,
            "languages": prof.languages[:6],
            "repos": [{"repo": r.repo, "merged": r.merged} for r in prof.repos[:6]],
        },
        "query": {"q": query, "location": location},
        "listings_seen": len(listings),
        "results": results,
        "searches": {"this_run": cache.searches_this_month() - before, "this_month": cache.searches_this_month(),
                     "budget": settings.monthly_budget},
    }
