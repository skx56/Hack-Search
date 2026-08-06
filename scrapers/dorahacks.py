from __future__ import annotations

import re
import time
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

from .models import Hackathon
from .utils import HEADERS

WEB3_HARD = (
    "defi",
    "solidity",
    "nft",
    "onchain",
    "tokenisation",
    "tokenization",
    "ethereum",
    "bitcoin",
    "algorand",
    "flare",
    "casper",
    "rwa",
    "depin",
)
WEB3_SOFT = ("web3", "blockchain", "crypto", "zk", "wallet", "buidl")
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
    "health",
    "education",
    "creative",
)


def scrape_dorahacks() -> list[Hackathon]:
    """Scrape DoraHacks listing + detail pages (public API is gone)."""
    session = requests.Session()
    session.headers.update(
        {
            **HEADERS,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": "https://dorahacks.io/",
        }
    )

    try:
        slugs = _discover_slugs(session)
    except Exception:
        return []

    results: list[Hackathon] = []
    seen: set[str] = set()

    for i, slug in enumerate(slugs):
        if slug in seen:
            continue
        seen.add(slug)
        if i:
            time.sleep(0.8)
        try:
            item = _parse_detail(session, slug)
        except Exception:
            continue
        if item:
            results.append(item)

    return results


def _discover_slugs(session: requests.Session) -> list[str]:
    slugs: list[str] = []
    seen: set[str] = set()
    skip = {"create", "organizer", "guide", "new", "host"}

    for status in ("ongoing", "upcoming"):
        resp = session.get(
            "https://dorahacks.io/hackathon",
            params={"status": status},
            timeout=30,
        )
        if resp.status_code != 200:
            continue
        for slug in re.findall(r"/hackathon/([a-zA-Z0-9_-]+)/?", resp.text):
            if slug in skip or slug in seen:
                continue
            seen.add(slug)
            slugs.append(slug)
    return slugs


def _parse_detail(session: requests.Session, slug: str) -> Hackathon | None:
    url = f"https://dorahacks.io/hackathon/{slug}/"
    resp = session.get(url, timeout=30)
    if resp.status_code != 200:
        return None

    soup = BeautifulSoup(resp.text, "lxml")
    text = " ".join(soup.get_text(" ", strip=True).split())
    title = (soup.title.string or "").split("|")[0].strip()
    if not title or "Hackathon" == title:
        return None

    mode = _mode(text)
    if mode not in {"online", "hybrid"}:
        return None

    tags = _tags(text)
    title_l = title.lower()
    blob = f"{title} {' '.join(tags)}".lower()
    # Keep AI-titled DoraHacks events even when the platform also tags Web3.
    ai_titled = any(k in title_l for k in ("ai", "agent", "llm", "genai", "creative", "intelligence"))
    if _is_web3_heavy(blob) and not ai_titled:
        return None
    if not ai_titled and not any(k in blob for k in AI_PRODUCT_KEYWORDS):
        # Still keep general virtual cash events that aren't crypto-heavy
        if _is_web3_heavy(blob):
            return None

    amount, currency, prize_text, has_cash = _prize(text)
    deadline = _deadline(text)
    start = _submission_start(text)

    og_image = None
    og = soup.find("meta", property="og:image")
    if og and og.get("content"):
        og_image = og["content"]

    return Hackathon(
        id=f"dorahacks-{slug}",
        title=title,
        url=url,
        source="DoraHacks",
        mode=mode,
        prize_amount=amount,
        prize_currency=currency,
        prize_text=prize_text,
        has_cash_prize=has_cash,
        submission_deadline=deadline,
        registration_deadline=deadline,
        start_date=start,
        end_date=deadline,
        organization=_org(text, tags),
        themes=tags[:8],
        status="open",
        location="Online" if mode == "online" else "Hybrid",
        thumbnail=og_image,
    )


def _mode(text: str) -> str:
    lower = text.lower()
    if "virtual hackathon" in lower or "online hackathon" in lower:
        return "online"
    if "hybrid" in lower:
        return "hybrid"
    if "in-person" in lower or "irl hackathon" in lower:
        return "offline"
    # DoraHacks listings are predominantly virtual; default soft-online when unclear
    if "virtual" in lower:
        return "online"
    return "unknown"


def _is_web3_heavy(blob: str) -> bool:
    if any(k in blob for k in WEB3_HARD):
        return True
    return sum(1 for k in WEB3_SOFT if k in blob) >= 2


def _tags(text: str) -> list[str]:
    m = re.search(
        r"Virtual Hackathon Tags\s+(.+?)(?:\s+web3 ecosystem\b|\s+FOLLOW US\b|\s+About Dora\b|\s+Submit BUIDL\b|\s+Register as Hacker\b)",
        text,
        re.I,
    )
    if not m:
        m = re.search(r"Tags\s+(.+?)(?:\s+FOLLOW US\b|\s+About Dora\b)", text, re.I)
    if not m:
        return []
    raw = m.group(1)
    parts = re.findall(
        r"(?:AI Agents|Creator Economy|Autonomous Trading|Trading Bots|Prediction Markets|"
        r"Algorithmic Trading|Machine Learning|Generative AI|Risk Management|"
        r"[A-Z][a-zA-Z0-9+#/.]*(?:\s+[A-Z][a-zA-Z0-9+#/.-]*){0,2})",
        raw,
    )
    out: list[str] = []
    for t in parts:
        t = t.strip(" ·|-")
        if 1 < len(t) <= 40 and t.lower() not in {
            "tags",
            "typescript",
            "solidity",
            "evm",
            "web3",
            "blockchain",
            "crypto",
            "defi",
        }:
            out.append(t)
    return out[:8]


def _org(text: str, tags: list[str]) -> str | None:
    for t in tags:
        if t.lower() in {"ai", "ai agents", "agents", "creator economy"}:
            continue
        if re.fullmatch(r"[A-Z][A-Za-z0-9&.\-]{1,30}", t):
            return t
    m = re.search(r"web3 ecosystem\s+([A-Z][A-Za-z0-9&.\- ]{1,40}?)\s+(?:Submission|TypeScript|FOLLOW)", text)
    if m:
        return m.group(1).strip()
    return None


def _prize(text: str) -> tuple[float | None, str | None, str | None, bool]:
    m = re.search(r"Prize Pool\s*([0-9][0-9,]*)\s*(USD|INR|EUR|USDT)?", text, re.I)
    if not m:
        return None, None, None, False
    amount = float(m.group(1).replace(",", ""))
    currency = (m.group(2) or "USD").upper()
    if currency == "USDT":
        currency = "USD"
    text_out = f"${amount:,.0f}" if currency == "USD" else f"{currency} {amount:,.0f}"
    return amount, currency, text_out, amount > 0


def _parse_dh_time(value: str) -> str | None:
    try:
        dt = datetime.strptime(value.strip(), "%Y/%m/%d %H:%M").replace(tzinfo=timezone.utc)
        return dt.isoformat()
    except ValueError:
        return None


def _deadline(text: str) -> str | None:
    m = re.search(r"Deadline\s+(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2})", text)
    if m:
        return _parse_dh_time(m.group(1))
    m = re.search(r"Submission\s+(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2})", text)
    if m:
        return _parse_dh_time(m.group(1))
    return None


def _submission_start(text: str) -> str | None:
    m = re.search(r"Submission\s+(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2})", text)
    if m:
        return _parse_dh_time(m.group(1))
    return None

