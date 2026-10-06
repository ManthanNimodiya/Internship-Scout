# Internship Scout

Your merged pull requests are the best CV you have. Internship Scout reads them, finds internships that match what
you've actually shipped, checks which companies are young and publish an email you can write to, and drafts a first
message that cites your own work. It never sends anything for you.

Built for the **SerpApi India Hackathon 2026**, *Knowledge & Public Interest* track.

## Why I built it

I'm a second-year student in Bengaluru with about 80 pull requests merged into open-source projects. In one week I
emailed nearly 50 companies about internships by hand, and most of that time went on the same four chores:

1. finding listings that were actually open to a student in India, not reposts on job boards;
2. checking whether a company was a young startup or a large firm;
3. finding an email address the company had *published*, rather than a guessed one or a support inbox;
4. working out which of my PRs were relevant to each role.

Internship Scout does those four things in about a minute, with every step explained.

## What it does

```
GitHub username ─▶ merged PRs in other people's repos ─▶ your real languages
                                                                │
Google Jobs (SerpApi) ─▶ listings ─▶ drop job-board reposts ─▶ shortlist
                                                                │
for each company:  Google Search (SerpApi) ─▶ founding year + website, verified to be the same company
                   company website / GitHub org ─▶ published hiring email
                   Google News (SerpApi, optional) ─▶ recent funding news
                                                                │
                              rank with plain-English reasons ─▶ draft email citing your best matching PR
```

Each result shows:

- a score and the reasons behind it, e.g. *"Uses Rust, TypeScript, which you've shipped merged PRs in"*,
  *"Young company, founded 2021"*, *"Looks limited to people in the US"*;
- the founding year **with its source**, the website, and the email **with the page it was published on**;
- the application links from Google Jobs;
- a draft email you can edit, open in your mail app or copy. Results can be downloaded as a CSV to use as an outreach tracker.

## How SerpApi is used

| SerpApi engine | Used for | Searches |
|---|---|---|
| `google_jobs` | Finding listings. "remote" in a query becomes Google Jobs' own work-from-home filter (`ltype=1`), which returns far fewer job-board reposts than the word does. | 1 per run |
| `google` | Founding year and website from the knowledge panel or result snippets, accepted only when they clearly name the same company | 1 per company |
| `google_news` | Optional: recent funding news, which adds to a company's score | 1 per company |

The free plan has 250 searches a month, so the app is careful with them:

- every response is cached in SQLite (jobs for a day, company checks for two weeks), so repeat searches are free;
- searches that return nothing are cached too;
- a monthly budget (240 by default) stops live searches before the plan runs out, while cached results keep working;
- company checks run only for the shortlist, never for every listing.

A typical run (1 job search, 6 companies) costs 7 searches; with news, 13.

## Ranking

| Signal | Points |
|---|---|
| Each of your languages the listing mentions (up to 3) | +1.5 |
| Title says intern, trainee, junior, entry level, new grad or fresher | +3 |
| Title says senior, staff, lead, manager… | −3 |
| Listing looks US-only | −3 |
| Remote / work from home | +1.5 |
| Based in India (if not remote) | +1 |
| Founded in the last 5 years | +2 |
| Founded more than 10 years ago | −1 |
| Recent funding news | +1 |
| Publishes an email you can write to | +1 |

## Being careful with other people's data

- Emails are only taken from the company's **own domain**: its website's home, careers, jobs, contact or about pages,
  or its GitHub organisation. Personal addresses on other domains (Gmail and so on) are ignored.
- Support, sales, privacy, billing, press and customer-care inboxes are skipped.
- A founding year or website is only used when it clearly belongs to the same company. A similar name is not enough;
  this is what stops "Tecell" being matched to TE Connectivity (founded 1941).
- Nothing is sent automatically. The draft is a starting point the student edits and sends themselves.

## Run it

Python 3.10 or newer.

```bash
git clone https://github.com/ManthanNimodiya/internship-scout
cd internship-scout
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then add your SerpApi key (and optionally a GitHub token)
uvicorn app:app --reload    # open http://localhost:8000
```

Command line:

```bash
python cli.py <github-username> --query "software engineer intern remote" --location India --companies 3
python cli.py <github-username> --query "software engineer intern" --location "Bengaluru, Karnataka, India" --news
```

Tests:

```bash
pip install -r requirements-dev.txt
pytest
```

## Project layout

```
app.py              FastAPI app: the page, /api/scout and /api/budget
cli.py              the same pipeline from the terminal
scout/serp.py       SerpApi client (Google Jobs, Google, Google News), cached and budgeted
scout/cache.py      SQLite cache and monthly search counter
scout/github.py     merged PRs and languages from the GitHub API
scout/companies.py  founding year, website and published email, with same-company checks
scout/rank.py       scoring with reasons, job-board and US-only detection
scout/drafts.py     picks your most relevant fix or feature per project and writes the email
static/             the web interface
tests/              unit tests for the matching, ranking and drafting rules
```

## Limits

- Google Jobs coverage varies: very specific searches (for example "rust intern" in India) can return nothing. The app
  says so and suggests broader wording.
- Many small companies publish no email at all; then the app points you to the application links instead of guessing.
- Without a `GITHUB_TOKEN`, GitHub's search API allows only a few requests a minute, so the GitHub-organisation email
  check may be skipped on large runs.

## Credits

Built by [Manthan Nimodiya](https://mnimodiya.com) with help from Claude Code (Anthropic) as a coding assistant.
Job, search and news data via [SerpApi](https://serpapi.com).

MIT licensed.
