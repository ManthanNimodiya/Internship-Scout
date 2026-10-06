from scout.companies import Company
from scout.drafts import best_pr, draft, mailto
from scout.github import Profile, PullRequest, RepoWork
from scout.rank import is_job_board, score, stack_overlap

PROFILE = Profile(
    username="student",
    name="A Student",
    total_merged=14,
    repos=[
        RepoWork("org/editor", 9, ["Rust", "TypeScript"], [
            PullRequest(1, "ci: bump action versions", "https://github.com/org/editor/pull/1"),
            PullRequest(2, "fix(pty): resize the terminal when the window changes", "https://github.com/org/editor/pull/2"),
        ]),
        RepoWork("org/api", 5, ["Go"], [PullRequest(3, "fix: map cancelled requests to Canceled", "https://github.com/org/api/pull/3")]),
    ],
    languages=["Rust", "TypeScript", "Go"],
)


def test_job_boards_are_detected():
    assert is_job_board("remote quest jobs", "Remote Quest Jobs")
    assert is_job_board("HireVault", "HireVault")
    assert not is_job_board("Moloco", "Jobgether")


def test_stack_overlap_does_not_match_inside_words():
    assert stack_overlap("We use Rust and React", ["Rust", "TypeScript", "Go"]) == ["Rust", "TypeScript"]
    assert stack_overlap("go-to-market strategy", ["Go"]) == []


def test_young_remote_intern_role_outranks_senior_us_only_role():
    intern = {"title": "Software Engineer Intern", "description": "Rust and TypeScript", "location": "Anywhere",
              "detected_extensions": {"work_from_home": True}}
    senior = {"title": "Senior Engineer (Remote US)", "description": "Rust", "location": "Anywhere"}
    young = Company("Acme", founded=2023, email="jobs@acme.dev")
    old = Company("BigCo", founded=1990)

    intern_score, reasons, overlap = score(intern, young, PROFILE)
    senior_score, senior_reasons, _ = score(senior, old, PROFILE)
    assert intern_score > senior_score
    assert overlap == ["Rust", "TypeScript"]
    assert "Young company, founded 2023" in reasons
    assert "Looks limited to people in the US" in senior_reasons


def test_funding_news_adds_a_reason():
    company = Company("Acme", news=[{"title": "Acme raises $4M seed round"}])
    _, reasons, _ = score({"title": "Intern"}, company, PROFILE)
    assert any("funding" in r for r in reasons)


def test_draft_cites_a_fix_rather_than_ci_noise():
    assert best_pr(PROFILE.repos[0], "terminal").number == 2
    email = draft(PROFILE, "Acme", "Rust Intern", ["Rust"], "Rust intern working on the terminal")
    assert "Hi Acme team," in email["body"]
    assert "resize the terminal" in email["body"]
    assert "bump action versions" not in email["body"]


def test_mailto_encodes_subject_and_body():
    link = mailto("jobs@acme.dev", "Hello & welcome", "Line one\nLine two")
    assert link.startswith("mailto:jobs@acme.dev?subject=Hello%20%26%20welcome&body=Line%20one%0ALine%20two")
