from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .companies import is_big_company
from .models import Hackathon
from .utils import http_get, parse_money


def scrape_techgig() -> list[Hackathon]:
    """TechGig / Times Internet hackathons — common for India corporate challenges."""
    listing = http_get("https://techgig.com/hackathons", timeout=30).text
    soup = BeautifulSoup(listing, "lxml")

    candidates: list[tuple[str, str]] = []
    seen: set[str] = set()
    for a in soup.select('a[href*="/hackathon/"]'):
        href = a.get("href") or ""
        if "utm_" in href:
            href = href.split("?")[0]
        if "/hackathon/" not in href:
            continue
        url = urljoin("https://techgig.com", href)
        slug = url.rstrip("/").split("/")[-1].lower()
        if not slug or slug in seen or slug in {"hackathon", "hackathons"}:
            continue
        seen.add(slug)
        title = " ".join(a.get_text(" ", strip=True).split())
        # Listing cards often glue description into the anchor; trim
        title = re.split(r"\s{2,}|(?:The screening|Submit valid|To screen)", title)[0].strip()
        if len(title) < 4:
            title = slug.replace("-", " ").title()
        candidates.append((title[:120], url))

    results: list[Hackathon] = []
    for title, url in candidates[:20]:
        try:
            html = http_get(url, timeout=25).text
        except Exception:
            continue
        text = BeautifulSoup(html, "lxml").get_text("\n", strip=True)
        blob = f"{title}\n{text}"

        if not re.search(r"online|virtual|remote", blob, re.I):
            # Still keep if big company
            if not is_big_company(title=title, organization=_org_from_text(text)):
                continue

        amount, currency, prize_text, has_reward = _prize(blob)
        if not has_reward and not is_big_company(title=title):
            continue

        deadline = _deadline(blob)
        org = _org_from_text(text) or ("TechGig Partner" if is_big_company(title=title) else "TechGig")

        results.append(
            Hackathon(
                id=f"techgig-{abs(hash(url)) % 10_000_000}",
                title=title,
                url=url.split("?")[0],
                source="TechGig",
                mode="online",
                prize_amount=amount,
                prize_currency=currency,
                prize_text=prize_text or ("Corporate challenge" if is_big_company(title=title) else None),
                has_cash_prize=bool(has_reward or is_big_company(title=title)),
                submission_deadline=deadline,
                registration_deadline=deadline,
                start_date=None,
                end_date=deadline,
                organization=org,
                themes=["India", "Corporate"],
                participants=None,
                status="open",
                location="Online",
                thumbnail=None,
            )
        )

    return results


def _prize(blob: str) -> tuple[float | None, str | None, str | None, bool]:
    m = re.search(
        r"(?:₹|Rs\.?|INR)\s*[0-9,]+(?:\s*\+)?\s*(?:Prize Pool|prize pool)?|(?:prize pool)[^\n₹$]{0,20}((?:₹|Rs\.?|INR|\$)\s*[0-9,]+)",
        blob,
        re.I,
    )
    if m:
        raw = m.group(0)
        amount, currency, text = parse_money(raw)
        # Sum unique large INR tiers if pool line is weak
        if not amount or amount < 1000:
            vals = []
            for piece in re.findall(r"₹\s*[0-9,]+", blob):
                a, _, _ = parse_money(piece)
                if a and a >= 1000:
                    vals.append(a)
            if vals:
                amount = max(vals)
                currency = "INR"
                text = f"INR {amount:,.0f}"
        if amount and amount > 0:
            return amount, currency or "INR", text or f"INR {amount:,.0f}", True
    return None, None, None, False


def _deadline(blob: str) -> str | None:
    m = re.search(
        r"(?:ends? on|end(?:s)?|deadline)\s*(?:on|:)?\s*([A-Za-z]+\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}[^\n]{0,30})",
        blob,
        re.I,
    )
    if m:
        return m.group(1).strip()
    m = re.search(r"([A-Za-z]+\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}\s+at\s+[0-9:. ]+(?:AM|PM)\s*IST)", blob, re.I)
    return m.group(1).strip() if m else None


def _org_from_text(text: str) -> str | None:
    for line in text.split("\n")[:40]:
        if re.search(r"times of india|et auto|snowflake|unisys|amazon|microsoft|google|adobe|flipkart", line, re.I):
            return line.strip()[:60]
    return None
