from scout import companies
from scout.companies import _founded_from, _same_company, _website_from, find_email


def test_same_company_ignores_suffixes_but_not_different_names():
    assert _same_company("Zed Industries", "Zed")
    assert _same_company("Moloco", "Moloco Inc.")
    assert _same_company("Plane", "Plane Software")
    assert not _same_company("Tecell", "TE Connectivity")


def test_founded_year_comes_from_matching_knowledge_panel_only():
    good = {"knowledge_graph": {"title": "Liveblocks", "founded": "2021"}}
    assert _founded_from(good, "Liveblocks") == (2021, "Google knowledge panel")

    other_company = {"knowledge_graph": {"title": "TE Connectivity", "founded": "1941"}}
    assert _founded_from(other_company, "Tecell") == (None, "")


def test_founded_year_from_snippet_must_mention_the_company():
    data = {"organic_results": [
        {"title": "Company", "snippet": "A company is founded in 1602 as a legal entity.", "link": "https://en.wikipedia.org/wiki/Company"},
        {"title": "About Tecell", "snippet": "Tecell was founded in 2021 in Bengaluru.", "link": "https://tecell.in/about"},
    ]}
    assert _founded_from(data, "Tecell") == (2021, "https://tecell.in/about")


def test_website_skips_profile_sites():
    data = {"organic_results": [
        {"link": "https://www.linkedin.com/company/tecell"},
        {"link": "https://tecell.in/"},
    ]}
    assert _website_from(data, "Tecell") == "https://tecell.in"


def test_find_email_prefers_hiring_inbox_and_skips_support(monkeypatch):
    pages = {
        "https://acme.dev/": "Write to support@acme.dev or hello@acme.dev",
        "https://acme.dev/careers": "Apply: jobs@acme.dev. Recruiter: someone@gmail.com",
    }
    monkeypatch.setattr(companies, "_fetch", lambda url: pages.get(url, ""))
    assert find_email("https://www.acme.dev") == ("jobs@acme.dev", "https://acme.dev/careers")


def test_find_email_never_returns_other_domains(monkeypatch):
    monkeypatch.setattr(companies, "_fetch", lambda url: "contact: founder@gmail.com, sales@acme.dev")
    assert find_email("https://acme.dev") == ("", "")
