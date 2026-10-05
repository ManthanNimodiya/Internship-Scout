"""Writes a short, specific first email from the student's own merged PRs. It never sends anything."""

import re
from urllib.parse import quote

from .github import Profile, PullRequest, RepoWork

# Fixes and features say more about a contributor than tests, CI or docs changes.
KIND = {"fix": 3, "feat": 3, "perf": 3, "refactor": 2, "test": 1, "ci": 0, "chore": 0, "docs": 0, "build": 0}


def best_pr(repo: RepoWork, job_text: str) -> PullRequest:
    words = set(re.findall(r"[a-z][a-z0-9+]{2,}", job_text.lower()))

    def rank(pr: PullRequest):
        kind = re.match(r"([a-z]+)", pr.title.lower())
        title_words = set(re.findall(r"[a-z][a-z0-9+]{2,}", pr.title.lower()))
        return (KIND.get(kind.group(1), 2) if kind else 2, len(words & title_words), len(pr.title))

    return max(repo.prs, key=rank)


def pick_evidence(profile: Profile, overlap: list[str], limit: int = 3) -> list[RepoWork]:
    """Prefer repos written in the languages the job asks for, then the repos with the most merged PRs."""
    wanted = set(overlap)
    return sorted(profile.repos, key=lambda r: (-len(wanted & set(r.languages)), -r.merged))[:limit]


def draft(profile: Profile, company: str, job_title: str, overlap: list[str], job_text: str = "") -> dict:
    evidence = pick_evidence(profile, overlap)
    lines = []
    for r in evidence:
        pr = best_pr(r, job_text)
        project = r.repo.split("/")[1]
        lines.append(f"- {project}: {r.merged} merged, e.g. \"{pr.title}\" ({pr.url})")

    stack = f" Your stack ({', '.join(overlap[:3])}) is where most of my work is." if overlap else ""
    subject = f"{job_title}: open-source contributor applying" if job_title else f"Internship at {company}"
    body = "\n".join([
        f"Hi {company} team,",
        "",
        f"I saw your {job_title} listing and would like to be considered, or for a remote internship if that suits you better.{stack}",
        "",
        f"I'm a student with {profile.total_merged} pull requests merged into other people's open-source projects. The most relevant:",
        *lines,
        "",
        f"GitHub: https://github.com/{profile.username}",
        "",
        "Best,",
        profile.name,
    ])
    return {"subject": subject, "body": body}


def mailto(to: str, subject: str, body: str) -> str:
    return f"mailto:{to}?subject={quote(subject)}&body={quote(body)}"
