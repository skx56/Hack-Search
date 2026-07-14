from __future__ import annotations

import re
from datetime import datetime, timezone

from .models import Hackathon
from .utils import http_get, http_get_json, parse_money


def scrape_hack2skill() -> list[Hackathon]:
    data = http_get_json(
        "https://hack2skill.com/api/v1/innovator/public/event/list",
        params={"page": 1, "records": 100},
    )
    payload = data.get("data") or {}
    events = []
    for key in ("flagshipEvents", "communityEvents"):
        events.extend(payload.get(key) or [])

    now = datetime.now(timezone.utc)
    results: list[Hackathon] = []
    seen: set[str] = set()

    for item in events:
        slug = item.get("eventUrl")
        title = (item.get("title") or "").strip()
        if not slug or not title or slug in seen:
            continue

        mode_raw = ((item.get("tags") or {}).get("mode") or {}).get("value") or ""
        mode = _mode(mode_raw)
        if mode not in {"online", "hybrid"}:
            continue

        reg_end = item.get("registrationEnd")
        if not _still_open(reg_end, now):
            continue

        seen.add(slug)
        url = (item.get("customEventUrl") or f"https://hack2skill.com/event/{slug}/").split("?")[0]
        amount, currency, prize_text, has_cash = _scrape_prize(url)

        tags = item.get("tags") or {}
        participants = ((tags.get("registrations") or {}).get("value"))
        tech = (tags.get("technology") or {}).get("value") or []
        if isinstance(tech, str):
            tech = [tech]

        results.append(
            Hackathon(
                id=f"hack2skill-{item.get('_id') or slug}",
                title=title,
                url=url,
                source="Hack2Skill",
                mode=mode,
                prize_amount=amount,
                prize_currency=currency,
                prize_text=prize_text,
                has_cash_prize=has_cash,
                submission_deadline=reg_end,
                registration_deadline=reg_end,
                start_date=item.get("registrationStart"),
                end_date=reg_end,
                organization="Hack2Skill",
                themes=[str(t) for t in tech][:6],
                participants=int(participants) if participants else None,
                status=item.get("status"),
                location="Online" if mode == "online" else "Hybrid",
                thumbnail=item.get("thumbnail"),
            )
        )

    return results


def _mode(value: str) -> str:
    v = (value or "").upper()
    if v in {"VIRTUAL", "ONLINE", "REMOTE"}:
        return "online"
    if v == "HYBRID":
        return "hybrid"
    return "offline"


def _still_open(reg_end: str | None, now: datetime) -> bool:
    if not reg_end:
        return True
    try:
        return datetime.fromisoformat(reg_end.replace("Z", "+00:00")) >= now
    except ValueError:
        return True


def _scrape_prize(url: str) -> tuple[float | None, str | None, str | None, bool]:
    try:
        html = http_get(url, timeout=25).text
    except Exception:
        return None, None, None, False

    # Normalize common INR encodings before matching
    normalized = (
        html.replace("&#8377;", "₹")
        .replace("&#x20b9;", "₹")
        .replace("&amp;#8377;", "₹")
        .replace("Rs.", "₹")
        .replace("Rs ", "₹ ")
        .replace("INR ", "₹")
    )

    rupee_matches = re.findall(r"₹\s*[0-9,]+", normalized)
    dollar_matches = re.findall(r"\$\s*[0-9,]{3,}", normalized)

    rupees = []
    for m in rupee_matches:
        amount, _, _ = parse_money(m)
        if amount and amount >= 1000:
            rupees.append(amount)
    dollars = []
    for m in dollar_matches:
        amount, _, _ = parse_money(m)
        if amount and amount >= 1000:
            dollars.append(amount)

    if rupees:
        unique = sorted(set(rupees), reverse=True)
        total = sum(unique[:6])
        return total, "INR", f"INR {total:,.0f}", True
    if dollars:
        # Prefer a single large pool figure over summing every tier mention
        amount = max(dollars)
        return amount, "USD", f"${amount:,.0f}", True
    return None, None, None, False
