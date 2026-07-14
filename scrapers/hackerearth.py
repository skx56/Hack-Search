from __future__ import annotations

import re

from .models import Hackathon
from .utils import http_get, http_get_json, parse_money


def scrape_hackerearth() -> list[Hackathon]:
    data = http_get_json("https://www.hackerearth.com/chrome-extension/events/")
    items = data.get("response") or []
    results: list[Hackathon] = []

    for item in items:
        url = item.get("url") or ""
        if "/hackathon/" not in url:
            continue

        title = (item.get("title") or "").strip()
        prize_amount, prize_currency, prize_text, has_cash = _guess_prize(item, url)

        # HackerEarth challenges listed here are typically remote/online
        results.append(
            Hackathon(
                id=f"hackerearth-{_slug(url)}",
                title=title,
                url=url,
                source="HackerEarth",
                mode="online",
                prize_amount=prize_amount,
                prize_currency=prize_currency,
                prize_text=prize_text,
                has_cash_prize=has_cash,
                submission_deadline=item.get("end_utc_tz") or item.get("end_tz"),
                registration_deadline=None,
                start_date=item.get("start_utc_tz") or item.get("start_tz"),
                end_date=item.get("end_utc_tz") or item.get("end_tz"),
                organization="HackerEarth",
                themes=[item.get("challenge_type")] if item.get("challenge_type") else [],
                participants=None,
                status=item.get("status"),
                location="Online",
                thumbnail=item.get("thumbnail"),
            )
        )

    return [h for h in results if h.has_cash_prize]


def _slug(url: str) -> str:
    return url.rstrip("/").split("/")[-1] or "unknown"


def _guess_prize(item: dict, url: str) -> tuple[float | None, str | None, str | None, bool]:
    blob = " ".join(
        str(x)
        for x in [item.get("title"), item.get("description"), item.get("challenge_type")]
        if x
    )
    amount, currency, text = parse_money(blob)
    if amount and amount > 0:
        return amount, currency, text, True

    # Light detail-page scan for prize mentions
    try:
        html = http_get(url, timeout=20).text
    except Exception:
        return None, None, None, False

    patterns = [
        r"Prize [Pp]ool[:\s]*([₹$€£]?\s*[0-9,]+\s*(?:USD|INR|EUR)?)",
        r"([₹$€£]\s*[0-9,]{3,})",
        r"worth\s+([₹$€£]?\s*[0-9,]+)",
    ]
    for pat in patterns:
        m = re.search(pat, html)
        if m:
            amount, currency, text = parse_money(m.group(1))
            if amount and amount > 0:
                return amount, currency, text, True
    return None, None, None, False
