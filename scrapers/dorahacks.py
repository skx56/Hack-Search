from __future__ import annotations

import re
from datetime import datetime, timezone

import requests

from .models import Hackathon
from .utils import HEADERS, parse_money

WEB3_KEYWORDS = (
    "web3",
    "blockchain",
    "crypto",
    "ethereum",
    "bitcoin",
    "defi",
    "nft",
    "onchain",
    "solidity",
    "zk",
    "tokenisation",
    "tokenization",
    "algorand",
    "casper",
    "wallet",
    "buidl",
)

AI_PRODUCT_KEYWORDS = (
    "ai",
    "artificial intelligence",
    "machine learning",
    "llm",
    "genai",
    "generative",
    "agent",
    "product",
    "saas",
    "enterprise",
    "iot",
    "smart city",
    "health",
    "education",
    "gnss",
    "space",
)


def scrape_dorahacks() -> list[Hackathon]:
    """Fetch DoraHacks via API (needs a warmed browser-like session)."""
    session = requests.Session()
    session.headers.update(
        {
            **HEADERS,
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://dorahacks.io/hackathon?status=ongoing",
            "Origin": "https://dorahacks.io",
        }
    )

    # Cloudflare / WAF warm-up
    session.get("https://dorahacks.io/hackathon?status=ongoing", timeout=30)

    raw: list[dict] = []
    for status in ("ongoing", "upcoming"):
        page = 1
        while page <= 5:
            resp = session.get(
                "https://dorahacks.io/api/hackathon/",
                params={"page": page, "page_size": 50, "status": status},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results") or []
            raw.extend(results)
            if not data.get("next"):
                break
            page += 1

    results: list[Hackathon] = []
    seen: set[str] = set()

    for item in raw:
        title = (item.get("title") or "").strip()
        uname = item.get("uname")
        if not title:
            continue

        mode = _mode(item.get("participation_form"))
        if mode not in {"online", "hybrid"}:
            continue

        fields = item.get("field") or []
        if isinstance(fields, str):
            fields = [f.strip() for f in fields.split(",") if f.strip()]
        elif isinstance(fields, list):
            # Sometimes API returns one comma-joined string inside the list
            expanded: list[str] = []
            for f in fields:
                if isinstance(f, str) and "," in f:
                    expanded.extend(x.strip() for x in f.split(",") if x.strip())
                else:
                    expanded.append(str(f))
            fields = expanded
        field_text = ", ".join(str(f) for f in fields)
        blob = f"{title} {field_text} {(item.get('description') or '')[:500]}".lower()

        # Prefer AI / product / general tech; skip crypto-heavy listings
        if _is_web3_heavy(blob):
            continue
        if not (_is_ai_product(blob) or _is_general_tech(blob)):
            # keep unknown/general virtual events lightly
            pass

        key = uname or title.lower()
        if key in seen:
            continue
        seen.add(key)

        amount, currency, prize_text, has_cash = _prize_from_description(item.get("description") or "")
        org = (item.get("organization") or {}).get("name")
        url = (
            f"https://dorahacks.io/hackathon/{uname}/detail"
            if uname
            else "https://dorahacks.io/hackathon"
        )

        start = _ts(item.get("start_time"))
        end = _ts(item.get("end_time"))

        results.append(
            Hackathon(
                id=f"dorahacks-{item.get('id') or key}",
                title=title,
                url=url,
                source="DoraHacks",
                mode=mode,
                prize_amount=amount,
                prize_currency=currency,
                prize_text=prize_text,
                has_cash_prize=has_cash,
                submission_deadline=end,
                start_date=start,
                end_date=end,
                organization=org,
                themes=[str(f) for f in fields][:8],
                participants=item.get("hackers_count") or item.get("applications_count"),
                status=str(item.get("status")),
                location="Online" if mode == "online" else (item.get("venue_name") or "Hybrid"),
                thumbnail=item.get("image_url"),
            )
        )

    return results


def _mode(value: str | None) -> str:
    v = (value or "").lower()
    if "virtual" in v or "online" in v:
        return "online"
    if "hybrid" in v:
        return "hybrid"
    if "irl" in v or "in person" in v:
        return "offline"
    return "unknown"


def _is_web3_heavy(blob: str) -> bool:
    hard = ("defi", "solidity", "nft", "onchain", "tokenisation", "tokenization", "ethereum", "bitcoin", "algorand", "flare", "casper")
    if any(k in blob for k in hard):
        return True
    soft = ("web3", "blockchain", "crypto", "zk", "wallet", "buidl")
    return sum(1 for k in soft if k in blob) >= 1


def _is_ai_product(blob: str) -> bool:
    return any(k in blob for k in AI_PRODUCT_KEYWORDS)


def _is_general_tech(blob: str) -> bool:
    return any(k in blob for k in ("hackathon", "innovation", "startup", "product", "iot", "space", "health"))


def _ai_primary(title: str, fields: str) -> bool:
    blob = f"{title} {fields}".lower()
    ai_hits = sum(1 for k in ("ai", "artificial intelligence", "machine learning", "generative", "agent") if k in blob)
    web3_hits = sum(1 for k in WEB3_KEYWORDS if k in blob)
    return ai_hits >= 1 and ai_hits > web3_hits


def _prize_from_description(desc: str) -> tuple[float | None, str | None, str | None, bool]:
    if not desc:
        return None, None, None, False

    # Explicit prize pool lines first
    pool = re.search(
        r"(?:prize pool|total prizes?|in prizes?)[^\n$₹]{0,40}([\$₹]\s*[0-9]{1,3}(?:,[0-9]{3})+(?:\s*USD)?|[\$₹]\s*[0-9]+k)",
        desc,
        re.I,
    )
    if pool:
        amount, currency, text = parse_money(pool.group(1))
        if amount:
            return amount, currency or "USD", text, True

    dollars = [parse_money(m)[0] for m in re.findall(r"\$\s*[0-9]{1,3}(?:,[0-9]{3})+", desc)]
    dollars = [a for a in dollars if a and a >= 1000]
    if dollars:
        # largest single mentioned prize / pool figure
        amount = max(dollars)
        return amount, "USD", f"${amount:,.0f}", True
    return None, None, None, False


def _ts(value) -> str | None:
    if not value:
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc).isoformat()
    except Exception:
        return None
