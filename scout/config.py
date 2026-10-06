import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    serpapi_key: str = os.getenv("SERPAPI_KEY", "")
    github_token: str = os.getenv("GITHUB_TOKEN", "")
    # The free SerpApi plan allows 250 searches a month; stop a little before that.
    monthly_budget: int = int(os.getenv("SCOUT_MONTHLY_BUDGET", "240"))
    cache_path: Path = Path(os.getenv("SCOUT_CACHE", str(ROOT / "scout-cache.sqlite3")))
    user_agent: str = "internship-scout/0.1 (+https://github.com/ManthanNimodiya/Internship-Scout)"


settings = Settings()
