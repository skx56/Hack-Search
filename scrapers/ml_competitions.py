from __future__ import annotations

import re
from datetime import datetime, timezone
from urllib.parse import urlparse, urlunparse

import requests

from .models import Hackathon
from .utils import HEADERS, parse_money

MLCONTESTS_JSON = (
    "https://raw.githubusercontent.com/mlcontests/mlcontests.github.io/master/competitions.json"
)

# Established ML / data-science competition platforms with public cash contests.
# Kaggle and Devpost have dedicated scrapers and are intentionally excluded.
SUPPORTED_PLATFORMS = {
    "AIcrowd",
    "Bitgrit",
    "CodaLab",
    "Codabench",
    "CrunchDAO",
    "DrivenData",
    "EvalAI",
    "Grand Challenge",
    "Hugging Face",
    "Solafune",
    "Synapse",
    "ThinkOnward",
    "Tianchi",
    "Trustii",
    "Trustii.io",
    "Zindi",
}


def scrape_ml_competitions() -> list[Hackathon]:
    """Fetch open cash-prize contests from reputable ML competition platforms."""
    resp = requests.get(MLCONTESTS_JSON, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    payload = resp.json()
    rows = payload.get("data") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        return []

    results: list[Hackathon] = []
    seen: set[str] = set()
    now = datetime.now(timezone.utc)

    for row in rows:
        if not isinstance(row, dict):
            continue

        platform = str(row.get("platform") or "").strip()
        if platform not in SUPPORTED_PLATFORMS:
            continue

        prize = str(row.get("prize") or "").strip()
        if not _is_cash_reward(prize):
            continue
        amount, currency, prize_text = parse_money(prize)
        if not amount or amount <= 0:
            continue

        title = str(row.get("name") or row.get("title") or "").strip()
        url = _clean_url(str(row.get("url") or ""))
        deadline = _parse_deadline(row.get("deadline"))
        if not title or not url or deadline is None:
            continue
        if datetime.fromisoformat(deadline.replace("Z", "+00:00")) < now:
            continue
        if url in seen:
            continue
        seen.add(url)

        tags = row.get("tags") or []
        if isinstance(tags, str):
            tags = [tags]
        themes = [str(tag) for tag in tags if tag][:6] or ["Machine Learning"]
        sponsor = str(row.get("sponsor") or platform).strip()
        slug = _slug(url, title)

        results.append(
            Hackathon(
                id=f"mlcontest-{platform.lower().replace(' ', '-')}-{slug}",
                title=title,
                url=url,
                source=platform,
                mode="online",
                prize_amount=amount,
                prize_currency=currency or "USD",
                prize_text=prize_text or prize,
                has_cash_prize=True,
                submission_deadline=deadline,
                registration_deadline=deadline,
                end_date=deadline,
                organization=sponsor,
                themes=themes,
                status="open",
                location="Online",
            )
        )

    return results


def _is_cash_reward(text: str) -> bool:
    lowered = (text or "").strip().lower()
    if not lowered or lowered in {"knowledge", "swag", "kudos", "jobs", "internship"}:
        return False
    if re.search(r"[$€£₹]\s*[0-9]", text) or re.search(
        r"\b(usd|eur|inr|gbp)\b", lowered
    ):
        return True
    amount, _, _ = parse_money(text)
    return bool(amount and amount > 0)


def _parse_deadline(value: str | None) -> str | None:
    if not value:
        return None
    text = str(value).strip()
    for fmt in (
        "%d %b %Y",
        "%d %B %Y",
        "%Y-%m-%d",
        "%b %d, %Y",
        "%B %d, %Y",
    ):
        try:
            dt = datetime.strptime(text, fmt).replace(
                hour=23, minute=59, tzinfo=timezone.utc
            )
            return dt.isoformat().replace("+00:00", "Z")
        except ValueError:
            continue
    return None


def _clean_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    parsed = urlparse(url)
    cleaned = parsed._replace(query="", fragment="")
    out = urlunparse(cleaned).rstrip("/")
    if out.startswith("http://"):
        out = "https://" + out[len("http://") :]
    return out


def _slug(url: str, title: str) -> str:
    path = urlparse(url).path.rstrip("/").split("/")[-1]
    raw = path or title
    return re.sub(r"[^a-z0-9]+", "-", raw.lower()).strip("-")[:80]
