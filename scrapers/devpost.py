from __future__ import annotations

import re

from .models import Hackathon
from .utils import http_get_json, parse_money


def scrape_devpost(pages: int = 5) -> list[Hackathon]:
    results: list[Hackathon] = []
    seen: set[str] = set()

    for page in range(1, pages + 1):
        data = http_get_json(
            "https://devpost.com/api/hackathons",
            params={
                "challenge_type[]": "online",
                "status[]": ["open", "upcoming"],
                "order_by": "prize-amount",
                "page": page,
                "per_page": 20,
            },
        )
        hackathons = data.get("hackathons") or []
        if not hackathons:
            break

        for item in hackathons:
            url = item.get("url") or ""
            if not url or url in seen:
                continue
            seen.add(url)

            prize_html = item.get("prize_amount") or ""
            amount, currency, prize_text = parse_money(prize_html)
            cash_count = (item.get("prizes_counts") or {}).get("cash") or 0
            has_cash = bool(cash_count) or (amount is not None and amount > 0)

            location = (item.get("displayed_location") or {}).get("location") or "Online"
            themes = [t.get("name") for t in (item.get("themes") or []) if t.get("name")]

            results.append(
                Hackathon(
                    id=f"devpost-{item.get('id')}",
                    title=(item.get("title") or "").strip(),
                    url=url,
                    source="Devpost",
                    mode="online",
                    prize_amount=amount,
                    prize_currency=currency or ("USD" if has_cash else None),
                    prize_text=prize_text,
                    has_cash_prize=has_cash,
                    submission_deadline=item.get("submission_period_dates"),
                    start_date=None,
                    end_date=None,
                    organization=item.get("organization_name"),
                    themes=themes,
                    participants=item.get("registrations_count"),
                    status=item.get("open_state"),
                    location=location,
                    thumbnail=_abs_url(item.get("thumbnail_url")),
                    time_left=item.get("time_left_to_submission"),
                )
            )

    return results


def _abs_url(url: str | None) -> str | None:
    if not url:
        return None
    if url.startswith("//"):
        return "https:" + url
    return url
