from __future__ import annotations

import re

from .companies import is_big_company
from .models import Hackathon
from .utils import CURRENCY_SYMBOLS, http_get_json, normalize_mode, parse_money


def scrape_unstop(pages: int = 12) -> list[Hackathon]:
    results: list[Hackathon] = []
    seen: set[int] = set()

    # Pull online + all regions so hybrid/corporate campus challenges are not missed,
    # then keep online/hybrid (and big-company hybrids tagged offline with online rounds).
    for region in ("online", None):
        for page in range(1, pages + 1):
            params = {
                "opportunity": "hackathons",
                "page": page,
                "per_page": 50,
            }
            if region:
                params["region"] = region
            data = http_get_json(
                "https://unstop.com/api/public/opportunity/search-new",
                params=params,
            )
            items = ((data.get("data") or {}).get("data")) or []
            if not items:
                break

            for item in items:
                hid = item.get("id")
                if not hid or hid in seen:
                    continue

                title = (item.get("title") or "").strip()
                org = (item.get("organisation") or {}).get("name")
                mode = normalize_mode(item.get("region"), default="online")
                corporate = is_big_company(title=title, organization=org)

                if mode == "offline" and not corporate:
                    continue
                if mode == "offline" and corporate:
                    mode = "hybrid"

                if mode not in {"online", "hybrid"}:
                    continue

                amount, currency, prize_text, has_reward = _prizes(item)
                if not has_reward and not corporate:
                    continue
                if not has_reward and corporate:
                    prize_text = "Internships / PPI / branded prizes"
                    has_reward = True

                seen.add(hid)
                regn = item.get("regnRequirements") or {}
                url = item.get("seo_url") or (
                    f"https://unstop.com/{item.get('public_url')}" if item.get("public_url") else None
                )
                if not url:
                    continue

                results.append(
                    Hackathon(
                        id=f"unstop-{hid}",
                        title=title,
                        url=url,
                        source="Unstop",
                        mode=mode,
                        prize_amount=amount,
                        prize_currency=currency,
                        prize_text=prize_text,
                        has_cash_prize=has_reward,
                        submission_deadline=item.get("end_date"),
                        registration_deadline=regn.get("end_regn_dt"),
                        start_date=item.get("start_date") or regn.get("start_regn_dt"),
                        end_date=item.get("end_date"),
                        organization=org,
                        themes=[t.get("name") for t in (item.get("filters") or []) if t.get("name")][:6],
                        participants=item.get("registerCount"),
                        status=item.get("status"),
                        location="Online" if mode == "online" else "Hybrid",
                        thumbnail=item.get("logoUrl2"),
                    )
                )

    return results


def _prizes(item: dict) -> tuple[float | None, str | None, str | None, bool]:
    prizes = item.get("prizes") or []
    cash_total = 0.0
    currency = "INR"
    extras: list[str] = []

    for prize in prizes:
        cash = prize.get("cash")
        if cash:
            cash_total += float(cash)
        cur = prize.get("currency") or prize.get("currencyCode")
        if cur:
            currency = CURRENCY_SYMBOLS.get(cur, cur if len(str(cur)) <= 4 else currency)

        others = prize.get("others") or ""
        if others:
            extras.append(others)
            # Stipend / embedded INR amounts in "others"
            for m in re.findall(r"(?:INR|₹|Rs\.?)\s*[0-9,]+", others, re.I):
                amount, _, _ = parse_money(m)
                if amount and amount >= 1000:
                    cash_total += amount
                    currency = "INR"

        if prize.get("pre_placement_internship") or prize.get("pre_placement_opportunity"):
            extras.append("PPI / Internship")

    if cash_total > 0:
        return cash_total, currency, f"{currency} {cash_total:,.0f}", True

    meaningful = [
        e
        for e in extras
        if re.search(
            r"macbook|internship|ppi|stipend|₹|inr|rs\.?|cash|prize|ipad|laptop|placement",
            e,
            re.I,
        )
    ]
    if meaningful:
        summary = meaningful[0]
        if len(summary) > 80:
            summary = summary[:77] + "..."
        return None, currency, summary, True

    return None, None, None, False
