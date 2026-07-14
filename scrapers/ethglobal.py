from __future__ import annotations

import re
from datetime import datetime, timezone

from .models import Hackathon
from .utils import http_get, parse_money


def scrape_ethglobal() -> list[Hackathon]:
    """ETHGlobal events — only keep clearly virtual editions with an explicit prize pool."""
    html = http_get("https://ethglobal.com/events", timeout=40).text
    results: list[Hackathon] = []
    seen: set[str] = set()

    # Prefer structured-ish anchors that look like event cards
    for m in re.finditer(
        r'href="((?:https://ethglobal\.com)?/events/([a-z0-9\-]+))"',
        html,
        re.I,
    ):
        path, slug = m.group(1), m.group(2).lower()
        if slug in seen or slug in {"events", "prizes", "schedule", "faq"}:
            continue
        seen.add(slug)

        url = path if path.startswith("http") else f"https://ethglobal.com{path}"
        start = max(0, m.start() - 300)
        end = min(len(html), m.end() + 800)
        window_html = html[start:end]
        window = re.sub(r"<[^>]+>", " ", window_html)
        window = re.sub(r"\s+", " ", window).strip()

        blob = f"{slug} {window}".lower()
        is_online = any(t in blob for t in ("online", "virtual", "remote"))
        if not is_online:
            continue

        # Skip obviously historical summits (no year or old year in nearby text)
        years = [int(y) for y in re.findall(r"\b(20\d{2})\b", window)]
        current_year = datetime.now(timezone.utc).year
        if years and max(years) < current_year:
            continue

        prize_m = re.search(
            r"(?:prize pool|in prizes|prizes?)\s*(?:of|:)?\s*(\$\s*[0-9]{1,3}(?:,[0-9]{3})+|\$\s*[0-9]+k)",
            window,
            re.I,
        )
        if not prize_m:
            # Also accept standalone large USD amounts near the word prize
            prize_m = re.search(
                r"\$\s*([0-9]{1,3}(?:,[0-9]{3}){1,}|[0-9]+k)\s+(?:in\s+)?prizes?",
                window,
                re.I,
            )
        if not prize_m:
            continue

        amount, currency, prize_text = parse_money(prize_m.group(0))
        if not amount or amount < 1000:
            continue

        title = slug.replace("-", " ").title()
        title_m = re.search(r"(ETH(?:Global)?\s+[A-Za-z0-9 .+\-]{2,50})", window)
        if title_m:
            title = title_m.group(1).strip()

        results.append(
            Hackathon(
                id=f"ethglobal-{slug}",
                title=title,
                url=url,
                source="ETHGlobal",
                mode="online",
                prize_amount=amount,
                prize_currency=currency or "USD",
                prize_text=prize_text or f"${amount:,.0f}",
                has_cash_prize=True,
                submission_deadline=None,
                start_date=None,
                end_date=None,
                organization="ETHGlobal",
                themes=["Web3", "Ethereum"],
                participants=None,
                status="upcoming",
                location="Online",
                thumbnail=None,
            )
        )

    return results
