from __future__ import annotations

from .models import Hackathon
from .utils import http_get_json, parse_money


def scrape_luma() -> list[Hackathon]:
    data = http_get_json(
        "https://api.lu.ma/discover/get-paginated-events",
        params={"pagination_limit": 40, "query": "hackathon"},
    )
    results: list[Hackathon] = []
    seen: set[str] = set()

    for entry in data.get("entries") or []:
        event = entry.get("event") or {}
        if event.get("location_type") != "online":
            continue

        api_id = event.get("api_id") or entry.get("api_id")
        url = event.get("url")
        if not url or not api_id or api_id in seen:
            continue
        if not url.startswith("http"):
            url = f"https://lu.ma/{url.lstrip('/')}"

        name = (event.get("name") or "").strip()
        amount, currency, prize_text = parse_money(name)
        # Luma rarely encodes prize in listing; keep online hackathons only if
        # name suggests prize OR always include and let cash filter drop them.
        has_cash = bool(amount and amount > 0)

        seen.add(api_id)
        results.append(
            Hackathon(
                id=f"luma-{api_id}",
                title=name,
                url=url,
                source="Luma",
                mode="online",
                prize_amount=amount,
                prize_currency=currency,
                prize_text=prize_text,
                has_cash_prize=has_cash,
                submission_deadline=event.get("end_at"),
                start_date=event.get("start_at") or entry.get("start_at"),
                end_date=event.get("end_at"),
                organization=((entry.get("calendar") or {}).get("name")),
                themes=[],
                participants=entry.get("guest_count"),
                status="upcoming",
                location="Online",
                thumbnail=event.get("cover_url") or (entry.get("cover_image") or {}).get("url"),
            )
        )

    return results
