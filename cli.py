"""Command-line run: python cli.py ManthanNimodiya --query "rust intern remote" --companies 3"""

import argparse
import json

from scout.pipeline import run


def main() -> None:
    p = argparse.ArgumentParser(description="Find internships that fit your merged open-source work.")
    p.add_argument("github", help="GitHub username")
    p.add_argument("--query", default="software engineer intern remote")
    p.add_argument("--location", default="India")
    p.add_argument("--companies", type=int, default=3, help="companies to check (about one search each)")
    p.add_argument("--news", action="store_true", help="also fetch recent news per company (one extra search each)")
    p.add_argument("--json", action="store_true", help="print the full result as JSON")
    a = p.parse_args()

    out = run(a.github, a.query, a.location, a.companies, with_news=a.news)
    if a.json:
        print(json.dumps(out, indent=2))
        return

    prof = out["profile"]
    print(f"{prof['name']}: {prof['total_merged']} merged PRs, mostly {', '.join(prof['languages'][:4])}")
    print(f"{out['listings_seen']} listings for '{a.query}' in {a.location}\n")
    for r in out["results"]:
        c, j = r["company"], r["job"]
        print(f"[{r['score']:>4}] {c['name']}: {j['title']} ({j['location']})")
        print(f"       founded {c['founded'] or '?'} | {c['website'] or 'no website found'} | {c['email'] or 'no published email'}")
        for reason in r["reasons"]:
            print(f"       - {reason}")
        print()
    s = out["searches"]
    print(f"SerpApi searches: {s['this_run']} this run, {s['this_month']}/{s['budget']} this month")


if __name__ == "__main__":
    main()
