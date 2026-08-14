from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from urllib.parse import urlparse, urlunparse

import requests

from .models import Hackathon
from .utils import HEADERS, parse_money

MLCONTESTS_JSON = (
    "https://raw.githubusercontent.com/mlcontests/mlcontests.github.io/master/competitions.json"
)
KAGGLE_API_LIST = "https://www.kaggle.com/api/v1/competitions/list"


def scrape_kaggle() -> list[Hackathon]:
    """Cash-prize Kaggle competitions (API if configured, else public mlcontests list)."""
    items = _from_kaggle_api()
    if items is None:
        items = _from_mlcontests()
    return items


def _from_kaggle_api() -> list[Hackathon] | None:
    user = (os.environ.get("KAGGLE_USERNAME") or "").strip()
    key = (os.environ.get("KAGGLE_KEY") or "").strip()
    if not user or not key:
        return None

    results: list[Hackathon] = []
    seen: set[str] = set()
    session = requests.Session()
    session.auth = (user, key)
    session.headers.update({**HEADERS, "Accept": "application/json"})

    for page in range(1, 6):
        resp = session.get(
            KAGGLE_API_LIST,
            params={
                "group": "general",
                "category": "all",
                "sortBy": "prize",
                "page": page,
            },
            timeout=30,
        )
        if resp.status_code != 200:
            if page == 1:
                return None
            break
        rows = resp.json()
        if not isinstance(rows, list) or not rows:
            break
        for row in rows:
            item = _from_api_row(row)
            if not item or item.url in seen:
                continue
            seen.add(item.url)
            results.append(item)
    return results


def _from_api_row(row: dict) -> Hackathon | None:
    reward = str(row.get("reward") or "").strip()
    if not _is_cash_reward(reward):
        return None
    amount, currency, prize_text = parse_money(reward)
    if not amount or amount <= 0:
        return None

    ref = (row.get("ref") or "").strip().strip("/")
    title = (row.get("title") or ref or "").strip()
    if not title:
        return None

    if ref.startswith("http"):
        url = _clean_url(ref)
        slug = url.rstrip("/").split("/")[-1]
    else:
        slug = ref.split("/")[-1]
        url = f"https://www.kaggle.com/competitions/{slug}"

    deadline = row.get("deadline")
    if isinstance(deadline, str) and deadline.endswith("+00:00"):
        deadline = deadline.replace("+00:00", "Z")

    category = row.get("category") or row.get("organizationName")
    themes = [str(category)] if category else ["Machine Learning"]

    return Hackathon(
        id=f"kaggle-{slug}",
        title=title,
        url=url,
        source="Kaggle",
        mode="online",
        prize_amount=amount,
        prize_currency=currency or "USD",
        prize_text=prize_text or reward,
        has_cash_prize=True,
        submission_deadline=deadline,
        registration_deadline=deadline,
        end_date=deadline,
        organization=str(row.get("organizationName") or "Kaggle"),
        themes=themes[:6],
        participants=row.get("teamCount"),
        status="open",
        location="Online",
    )


def _from_mlcontests() -> list[Hackathon]:
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
        platform = str(row.get("platform") or "").lower()
        raw_url = str(row.get("url") or "")
        if platform != "kaggle" and "kaggle.com/competitions/" not in raw_url.lower():
            continue

        prize = str(row.get("prize") or "").strip()
        if not _is_cash_reward(prize):
            continue
        amount, currency, prize_text = parse_money(prize)
        if not amount or amount <= 0:
            continue

        title = (row.get("name") or row.get("title") or "").strip()
        url = _clean_url(raw_url)
        if not title or not url or "kaggle.com/competitions/" not in url:
            # Prefer linked Kaggle URL from additional_urls when primary host isn't Kaggle
            for extra in row.get("additional_urls") or []:
                extra_u = _clean_url(str(extra))
                if "kaggle.com/competitions/" in extra_u:
                    url = extra_u
                    break
            else:
                continue
        if url in seen:
            continue

        deadline = _parse_ml_deadline(row.get("deadline"))
        if deadline is None:
            continue
        if datetime.fromisoformat(deadline.replace("Z", "+00:00")) < now:
            continue

        seen.add(url)
        slug = url.rstrip("/").split("/")[-1]
        tags = row.get("tags") or []
        if isinstance(tags, str):
            tags = [tags]
        themes = [str(t) for t in tags if t][:6] or ["Machine Learning"]

        results.append(
            Hackathon(
                id=f"kaggle-{slug}",
                title=title,
                url=url,
                source="Kaggle",
                mode="online",
                prize_amount=amount,
                prize_currency=currency or "USD",
                prize_text=prize_text or prize,
                has_cash_prize=True,
                submission_deadline=deadline,
                registration_deadline=deadline,
                end_date=deadline,
                organization=str(row.get("sponsor") or "Kaggle"),
                themes=themes,
                status="open",
                location="Online",
            )
        )

    return results


def _is_cash_reward(text: str) -> bool:
    t = (text or "").strip().lower()
    if not t or t in {"knowledge", "swag", "kudos", "jobs", "internship", "jobs & internship"}:
        return False
    if re.search(r"[$€£₹]\s*[0-9]", text) or re.search(r"\b(usd|eur|inr|gbp)\b", t):
        return True
    amount, _, _ = parse_money(text)
    return bool(amount and amount > 0)


def _parse_ml_deadline(value: str | None) -> str | None:
    if not value:
        return None
    text = str(value).strip()
    for fmt in ("%d %b %Y", "%d %B %Y", "%Y-%m-%d", "%b %d, %Y", "%B %d, %Y"):
        try:
            dt = datetime.strptime(text, fmt).replace(hour=23, minute=59, tzinfo=timezone.utc)
            return dt.isoformat().replace("+00:00", "Z")
        except ValueError:
            continue
    return None


def _clean_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    parsed = urlparse(url)
    # Drop tracker query params like ?ref=mlcontests
    cleaned = parsed._replace(query="", fragment="")
    out = urlunparse(cleaned).rstrip("/")
    if out.startswith("http://"):
        out = "https://" + out[len("http://") :]
    return out
