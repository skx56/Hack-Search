from __future__ import annotations

from datetime import datetime, timezone

from .models import Hackathon
from .utils import http_get_json


def scrape_devfolio(pages: int = 3) -> list[Hackathon]:
    results: list[Hackathon] = []
    seen: set[str] = set()
    now = datetime.now(timezone.utc)

    # Prefer currently open / upcoming online events
    for filter_name in ("application_open", "online"):
        for page in range(1, pages + 1):
            data = http_get_json(
                "https://api.devfolio.co/api/hackathons",
                params={"filter": filter_name, "page": page, "limit": 20},
            )
            items = data.get("result") or []
            if not items:
                break

            for item in items:
                slug = item.get("slug")
                uuid = item.get("uuid")
                if not slug or slug in seen:
                    continue
                if not item.get("is_online"):
                    continue
                if not _is_active(item, now):
                    continue
                seen.add(slug)

                prize_amount, prize_currency, prize_text, has_cash = _fetch_prizes(slug)
                if not has_cash:
                    continue

                results.append(
                    Hackathon(
                        id=f"devfolio-{uuid or slug}",
                        title=(item.get("name") or "").strip(),
                        url=f"https://devfolio.co/hackathons/{slug}",
                        source="Devfolio",
                        mode="online",
                        prize_amount=prize_amount,
                        prize_currency=prize_currency,
                        prize_text=prize_text,
                        has_cash_prize=has_cash,
                        submission_deadline=item.get("ends_at"),
                        start_date=item.get("starts_at"),
                        end_date=item.get("ends_at"),
                        organization=None,
                        themes=[],
                        participants=_safe_int(item.get("approx_participant")),
                        status=item.get("status"),
                        location="Online",
                        thumbnail=item.get("cover_img"),
                    )
                )

    return results


def _is_active(item: dict, now: datetime) -> bool:
    ends = item.get("ends_at")
    if not ends:
        return True
    try:
        end_dt = datetime.fromisoformat(ends.replace("Z", "+00:00"))
        return end_dt >= now
    except ValueError:
        return True


def _fetch_prizes(slug: str) -> tuple[float | None, str | None, str | None, bool]:
    try:
        prizes = http_get_json(f"https://api.devfolio.co/api/hackathons/{slug}/prizes")
    except Exception:
        return None, None, None, False

    total = 0.0
    currency = None
    for prize in prizes or []:
        try:
            amount = float(prize.get("amount") or 0)
        except (TypeError, ValueError):
            amount = 0.0
        if amount > 0:
            total += amount
            currency = prize.get("currency") or currency or "USD"

    if total > 0:
        cur = currency or "USD"
        return total, cur, f"{cur} {total:,.0f}", True
    return None, None, None, False


def _safe_int(value) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None
