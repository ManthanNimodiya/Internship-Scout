"""Scores a job for a student: does it fit their stack, is it open to them, and is the company young enough to take a chance on them?

Every point comes with a plain-English reason so the student can see why a company ranks where it does.
"""

import re
from datetime import date

from .companies import Company
from .github import Profile

JUNIOR = re.compile(r"\b(intern(ship)?|trainee|junior|entry[- ]level|new grad|graduate|fresher|student)\b", re.I)
SENIOR = re.compile(r"\b(senior|sr\.?|staff|principal|lead|head of|director|manager|architect)\b|\b([5-9]|1\d)\+? years", re.I)
US_ONLY = re.compile(r"\b(remote[ ,-]*us|us[- ]only|usa only|us[- ]based|united states only|must be (located|based) in the us)\b", re.I)
BOARD_WORDS = re.compile(r"\b(jobs?|hire|hiring|careers?|recruit\w*|staffing|talent|remote|vacanc\w*|openings)\b", re.I)


def is_job_board(company: str, via: str) -> bool:
    """Listings reposted by job boards name the board as the company, so you can't write to the employer."""
    c, v = re.sub(r"[^a-z0-9]", "", company.lower()), re.sub(r"[^a-z0-9]", "", (via or "").lower().removeprefix("via "))
    return bool(BOARD_WORDS.search(company)) or (bool(c) and c == v)


REMOTE = re.compile(r"\b(remote|work from home|wfh|anywhere)\b", re.I)

# GitHub language names mapped to words that show up in job descriptions.
ALIASES = {
    "TypeScript": ["typescript", "ts", "node", "react", "next.js"],
    "JavaScript": ["javascript"],
    "Rust": ["rust", "tokio"],
    "Go": ["golang", "go developer", "go engineer", "in go"],
    "Python": ["python", "django", "fastapi", "flask"],
    "Swift": ["swift", "ios", "swiftui"],
    "Kotlin": ["kotlin", "android"],
    "C++": ["c++", "cpp"],
    "Solidity": ["solidity", "web3", "ethereum"],
}


def stack_overlap(text: str, languages: list[str]) -> list[str]:
    low = text.lower()
    found = []
    for lang in languages:
        words = ALIASES.get(lang, [lang.lower()])
        if any(re.search(rf"(?<![a-z]){re.escape(w)}(?![a-z])", low) for w in words):
            found.append(lang)
    return found


def score(job: dict, company: Company | None, profile: Profile) -> tuple[float, list[str], list[str]]:
    text = f"{job.get('title', '')}\n{job.get('description', '')}"
    title = job.get("title", "")
    points, reasons = 0.0, []

    overlap = stack_overlap(text, profile.languages[:8])
    if overlap:
        points += min(3, len(overlap)) * 1.5
        reasons.append(f"Uses {', '.join(overlap[:3])}, which you've shipped merged PRs in")

    if JUNIOR.search(title):
        points += 3
        reasons.append("Open to interns or early-career engineers")
    elif SENIOR.search(title):
        points -= 3
        reasons.append("Listed as a senior role, so ask about an internship instead")

    if US_ONLY.search(f"{title} {job.get('description', '')[:400]}"):
        points -= 3
        reasons.append("Looks limited to people in the US")

    ext = job.get("detected_extensions") or {}
    if ext.get("work_from_home") or REMOTE.search(f"{title} {job.get('location', '')}"):
        points += 1.5
        reasons.append("Remote")
    elif "india" in job.get("location", "").lower():
        points += 1
        reasons.append(f"Based in {job.get('location')}")

    if company and company.founded:
        age = date.today().year - company.founded
        if age <= 5:
            points += 2
            reasons.append(f"Young company, founded {company.founded}")
        elif age > 10:
            points -= 1
            reasons.append(f"Established company, founded {company.founded}")
    funding = re.compile(r"\b(raises?|raised|funding|seed|series [a-d]|backed by)\b", re.I)
    for item in (company.news if company else []):
        if funding.search(item.get("title") or ""):
            points += 1
            reasons.append(f"Recently in the news for funding: \u201c{item['title']}\u201d")
            break

    if company and company.email:
        points += 1
        reasons.append("Publishes an email you can write to")

    return round(points, 1), reasons, overlap
