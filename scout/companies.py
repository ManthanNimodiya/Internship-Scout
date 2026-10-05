"""Company checks: founding year and website from Google, and a published hiring email from the company's own site."""

import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

import httpx

from . import cache, serp
from .config import settings

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
YEAR_RE = re.compile(r"\b(?:founded|established|started)(?: in)?[^0-9]{0,20}((?:19|20)\d{2})\b", re.I)

HIRING = ("jobs", "careers", "career", "hiring", "talent", "recruit", "join", "work")
GENERAL = ("hello", "hi", "hey", "team", "contact", "info", "founders")
SKIP = ("support", "help", "sales", "privacy", "security", "billing", "press", "media", "legal", "abuse",
        "noreply", "no-reply", "marketing", "dpo", "gdpr", "partners", "invoice", "accounts")
PAGES = ("", "careers", "jobs", "contact", "about", "company")


@dataclass
class Company:
    name: str
    website: str = ""
    founded: int | None = None
    founded_source: str = ""
    description: str = ""
    email: str = ""
    email_source: str = ""
    news: list[dict] = field(default_factory=list)


def _domain(url: str) -> str:
    host = urlparse(url if "//" in url else f"https://{url}").netloc.lower()
    return host.removeprefix("www.")


def _founded_from(data: dict) -> tuple[int | None, str]:
    kg = data.get("knowledge_graph") or {}
    for key, value in kg.items():
        if "found" in key.lower():
            m = re.search(r"(?:19|20)\d{2}", str(value))
            if m:
                return int(m.group()), "Google knowledge panel"
    for res in data.get("organic_results", [])[:6]:
        m = YEAR_RE.search(f"{res.get('title', '')} {res.get('snippet', '')}")
        if m:
            return int(m.group(1)), res.get("link", "")
    return None, ""


def _website_from(data: dict, name: str) -> str:
    kg = data.get("knowledge_graph") or {}
    if kg.get("website"):
        return kg["website"]
    slug = re.sub(r"[^a-z0-9]", "", name.lower())
    noise = ("linkedin.", "wikipedia.", "crunchbase.", "glassdoor.", "indeed.", "naukri.", "ambitionbox.",
             "twitter.", "x.com", "facebook.", "instagram.", "youtube.", "github.com", "tracxn.", "zoominfo.")
    for res in data.get("organic_results", [])[:6]:
        link = res.get("link", "")
        dom = _domain(link)
        if slug and slug[:6] in dom.replace("-", "").replace(".", "") and not any(n in dom for n in noise):
            return f"https://{dom}"
    return ""


def _fetch(url: str) -> str:
    key = f"page:{url}"
    hit = cache.get(key, ttl_hours=24 * 7)
    if hit is not None:
        return hit
    try:
        r = httpx.get(url, timeout=12, follow_redirects=True, headers={"User-Agent": settings.user_agent})
        text = r.text if r.status_code == 200 and "html" in r.headers.get("content-type", "") else ""
    except httpx.HTTPError:
        text = ""
    cache.put(key, text)
    return text


def find_email(website: str) -> tuple[str, str]:
    """Best published address on the company's own domain. Hiring inboxes beat general ones; support and sales are skipped."""
    domain = _domain(website)
    if not domain:
        return "", ""
    best: tuple[int, str, str] = (0, "", "")
    for page in PAGES:
        url = f"https://{domain}/{page}"
        for email in set(EMAIL_RE.findall(_fetch(url))):
            local, _, host = email.lower().partition("@")
            if not (host == domain or host.endswith("." + domain)) or local.startswith(SKIP):
                continue
            rank = 3 if local.startswith(HIRING) else 2 if local.startswith(GENERAL) else 1
            if rank > best[0]:
                best = (rank, email.lower(), url)
        if best[0] == 3:
            break
    return best[1], best[2]


def enrich(name: str, with_news: bool = False) -> Company:
    data = serp.google(f"{name} company founded")
    founded, source = _founded_from(data)
    website = _website_from(data, name)
    kg = data.get("knowledge_graph") or {}
    company = Company(
        name=name,
        website=website,
        founded=founded,
        founded_source=source,
        description=kg.get("description", "") or (data.get("organic_results") or [{}])[0].get("snippet", ""),
    )
    if website:
        company.email, company.email_source = find_email(website)
    if with_news:
        company.news = [
            {"title": n.get("title"), "source": (n.get("source") or {}).get("name"), "date": n.get("date"), "link": n.get("link")}
            for n in serp.news(f'"{name}" funding OR raises OR launches')[:3]
        ]
    return company
