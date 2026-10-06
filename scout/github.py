"""Builds a contributor profile from a GitHub user's merged pull requests in other people's repos."""

from collections import Counter
from dataclasses import dataclass, field

import httpx

from . import cache
from .config import settings

API = "https://api.github.com"
# Markup, config and build files are not languages anyone hires for.
NOT_LANGUAGES = {"MDX", "Dockerfile", "Shell", "CSS", "SCSS", "HTML", "Makefile", "Nix", "Batchfile", "PowerShell",
                 "Jinja", "HCL", "Procfile", "Smarty", "Handlebars", "Starlark", "CMake", "Just"}


@dataclass
class PullRequest:
    number: int
    title: str
    url: str


@dataclass
class RepoWork:
    repo: str
    merged: int
    languages: list[str]
    prs: list[PullRequest] = field(default_factory=list)


@dataclass
class Profile:
    username: str
    name: str
    total_merged: int
    repos: list[RepoWork]
    languages: list[str]  # ranked by how many merged PRs touch a repo in that language


def get(path: str, **params):
    """Cached GitHub REST call. Also used by the company checks to find a company's GitHub organisation."""
    key = f"github:{path}:{sorted(params.items())}"
    hit = cache.get(key, ttl_hours=6)
    if hit is not None:
        return hit
    headers = {"Accept": "application/vnd.github+json", "User-Agent": settings.user_agent}
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"
    r = httpx.get(f"{API}{path}", params=params, headers=headers, timeout=30)
    r.raise_for_status()
    data = r.json()
    cache.put(key, data)
    return data


def profile(username: str, top_repos: int = 8) -> Profile:
    user = get(f"/users/{username}")
    items = get("/search/issues", q=f"author:{username} is:pr is:merged", per_page=100, sort="updated")["items"]

    by_repo: dict[str, list[PullRequest]] = {}
    for it in items:
        repo = it["repository_url"].split("/repos/")[1]
        if repo.split("/")[0].lower() == username.lower():
            continue  # only count work reviewed and merged by someone else
        by_repo.setdefault(repo, []).append(PullRequest(it["number"], it["title"], it["html_url"]))

    ranked = sorted(by_repo.items(), key=lambda kv: -len(kv[1]))
    repos: list[RepoWork] = []
    weight: Counter = Counter()
    for i, (repo, prs) in enumerate(ranked):
        langs: list[str] = []
        if i < top_repos:  # keep GitHub API calls bounded
            langs = [l for l in get(f"/repos/{repo}/languages") if l not in NOT_LANGUAGES][:4]
            for lang in langs:
                weight[lang] += len(prs)
        repos.append(RepoWork(repo, len(prs), langs, prs))

    return Profile(
        username=user["login"],
        name=user.get("name") or user["login"],
        total_merged=sum(r.merged for r in repos),
        repos=repos,
        languages=[lang for lang, _ in weight.most_common()],
    )
