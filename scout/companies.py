"""Company checks: founding year and website from Google, and a published hiring email from the company's own site."""

import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

import httpx

from . import cache, github, serp
from .config import settings

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
YEAR_RE = re.compile(r"\b(?:founded|established|started)(?: in)?[^0-9]{0,20}((?:19|20)\d{2})\b", re.I)

HIRING = ("jobs", "careers", "career", "hiring", "talent", "recruit", "join", "work")
GENERAL = ("hello", "hi", "hey", "team", "contact", "info", "founders")
SKIP = ("support", "help", "care", "customer", "sales", "privacy", "security", "billing", "press", "media", "legal", "abuse",
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


SUFFIXES = re.compile(r"\b(inc|llc|ltd|limited|pvt|private|gmbh|corp|corporation|co|company|technologies|technology|"
                      r"tech|labs|industries|software|solutions|systems|group|hq|ai|io)\b\.?", re.I)


def _slug(text: str) -> str:
    base = SUFFIXES.sub("", text) or text
    return re.sub(r"[^a-z0-9]", "", base.lower())


def _same_company(name: str, text: str) -> bool:
    """Guards against Google answering for a different organisation with a similar name."""
    a, b = _slug(name), _slug(text)
    return bool(a) and (a in b or (len(b) >= 4 and b in a))


def _founded_from(data: dict, name: str) -> tuple[int | None, str]:
    kg = data.get("knowledge_graph") or {}
    if _same_company(name, kg.get("title", "")):
        for key, value in kg.items():
            if "found" in key.lower():
                m = re.search(r"(?:19|20)\d{2}", str(value))
                if m:
                    return int(m.group()), "Google knowledge panel"
    for res in data.get("organic_results", [])[:6]:
        text = f"{res.get('title', '')} {res.get('snippet', '')}"
        m = YEAR_RE.search(text)
        if m and _same_company(name, text) and _slug(name) in _slug(text[: m.start()] + text[m.end():]):
            return int(m.group(1)), res.get("link", "")
    return None, ""


def _website_from(data: dict, name: str) -> str:
    kg = data.get("knowledge_graph") or {}
    if kg.get("website") and _same_company(name, kg.get("title", "")):
        return kg["website"]
    slug = _slug(name)
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
            if not _usable(email, domain):
                continue
            local = email.lower().partition("@")[0]
            rank = 3 if local.startswith(HIRING) else 2 if local.startswith(GENERAL) else 1
            if rank > best[0]:
                best = (rank, email.lower(), url)
        if best[0] == 3:
            break
    return best[1], best[2]


def github_org(name: str, website: str) -> dict:
    """The company's GitHub organisation, if it has one. Orgs often list a contact address and their site.

    An org only counts as a match when its website is the company's website, or, if we have no website,
    when its display name is clearly the same company.
    """
    try:
        hits = github.get("/search/users", q=f"{name} type:org", per_page=3).get("items", [])
        for hit in hits:
            org = github.get(f"/orgs/{hit['login']}")
            blog = _domain(org.get("blog") or "")
            if website and blog:
                if blog == _domain(website):
                    return org
            elif not website and _same_company(name, org.get("name") or org["login"]):
                return org
    except httpx.HTTPError:
        pass  # GitHub's search rate limit is tight without a token; the org check is a bonus, not a requirement
    return {}


def _usable(email: str, domain: str) -> bool:
    local, _, host = email.lower().partition("@")
    return bool(domain) and (host == domain or host.endswith("." + domain)) and not local.startswith(SKIP)


def enrich(name: str, with_news: bool = False) -> Company:
    data = serp.google(f'"{name}" company')
    founded, source = _founded_from(data, name)
    website = _website_from(data, name)
    kg = data.get("knowledge_graph") or {}
    company = Company(
        name=name,
        website=website,
        founded=founded,
        founded_source=source,
        description=kg.get("description", "") if _same_company(name, kg.get("title", "")) else "",
    )
    if website:
        company.email, company.email_source = find_email(website)

    if not company.email:
        org = github_org(name, website)
        if org:
            if not company.website and org.get("blog"):
                company.website = org["blog"] if "//" in org["blog"] else f"https://{org['blog']}"
                company.email, company.email_source = find_email(company.website)
            org_email = (org.get("email") or "").lower()
            if not company.email and _usable(org_email, _domain(company.website)):
                company.email, company.email_source = org_email, org.get("html_url", "")
    if with_news:
        company.news = [
            {"title": n.get("title"), "source": (n.get("source") or {}).get("name"), "date": n.get("date"), "link": n.get("link")}
            for n in serp.news(f'"{name}" funding OR raises OR launches')[:3]
        ]
    return company
