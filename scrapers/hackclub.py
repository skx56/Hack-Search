from __future__ import annotations

from .models import Hackathon
from .utils import http_get_json


def scrape_hackclub() -> list[Hackathon]:
    """Hack Club listings are usually community events without cash prizes."""
    items = http_get_json("https://hackathons.hackclub.com/api/events/upcoming")
    results: list[Hackathon] = []

    for item in items or []:
        if not item.get("virtual"):
            continue
        website = item.get("website")
        if not website:
            continue

        results.append(
            Hackathon(
                id=f"hackclub-{item.get('id')}",
                title=(item.get("name") or "").strip(),
                url=website,
                source="Hack Club",
                mode="online",
                prize_amount=None,
                prize_currency=None,
                prize_text=None,
                has_cash_prize=False,
                submission_deadline=item.get("end"),
                start_date=item.get("start"),
                end_date=item.get("end"),
                organization="Hack Club",
                themes=[],
                participants=None,
                status="upcoming",
                location="Online",
                thumbnail=item.get("logo") or item.get("banner"),
            )
        )

    return results
