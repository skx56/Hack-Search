from __future__ import annotations

from .models import Hackathon
from .utils import CURRENCY_SYMBOLS, http_get_json, normalize_mode


def scrape_unstop(pages: int = 8) -> list[Hackathon]:
    results: list[Hackathon] = []
    seen: set[int] = set()

    for page in range(1, pages + 1):
        data = http_get_json(
            "https://unstop.com/api/public/opportunity/search-new",
            params={
                "opportunity": "hackathons",
                "page": page,
                "per_page": 50,
                "region": "online",
            },
        )
        items = ((data.get("data") or {}).get("data")) or []
        if not items:
            break

        for item in items:
            hid = item.get("id")
            if not hid or hid in seen:
                continue
            seen.add(hid)

            mode = normalize_mode(item.get("region"), default="online")
            if mode != "online":
                continue

            prizes = item.get("prizes") or []
            cash_total = 0.0
            currency = "INR"
            for prize in prizes:
                cash = prize.get("cash")
                if cash:
                    cash_total += float(cash)
                cur = prize.get("currency") or prize.get("currencyCode")
                if cur:
                    currency = CURRENCY_SYMBOLS.get(cur, cur if len(str(cur)) <= 4 else currency)

            has_cash = cash_total > 0
            if not has_cash:
                continue

            regn = item.get("regnRequirements") or {}
            org = (item.get("organisation") or {}).get("name")
            url = item.get("seo_url") or (
                f"https://unstop.com/{item.get('public_url')}" if item.get("public_url") else None
            )
            if not url:
                continue

            results.append(
                Hackathon(
                    id=f"unstop-{hid}",
                    title=(item.get("title") or "").strip(),
                    url=url,
                    source="Unstop",
                    mode="online",
                    prize_amount=cash_total,
                    prize_currency=currency,
                    prize_text=f"{currency} {cash_total:,.0f}",
                    has_cash_prize=True,
                    submission_deadline=item.get("end_date"),
                    registration_deadline=regn.get("end_regn_dt"),
                    start_date=item.get("start_date") or regn.get("start_regn_dt"),
                    end_date=item.get("end_date"),
                    organization=org,
                    themes=[t.get("name") for t in (item.get("filters") or []) if t.get("name")][:6],
                    participants=item.get("registerCount"),
                    status=item.get("status"),
                    location="Online",
                    thumbnail=item.get("logoUrl2"),
                )
            )

    return results
