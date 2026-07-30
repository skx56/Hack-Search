from __future__ import annotations

import re
from datetime import datetime
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

from .companies import is_big_company
from .models import Hackathon
from .utils import http_get_json, normalize_mode, parse_money

IST = ZoneInfo("Asia/Kolkata")


def scrape_internshala(pages: int = 4) -> list[Hackathon]:
    """Internshala competitions API — strong coverage of India corporate hackathons."""
    results: list[Hackathon] = []
    seen: set[int] = set()

    for page in range(1, pages + 1):
        posts = http_get_json(
            "https://internshala.com/competitions/wp-json/wp/v2/posts",
            params={
                "categories": 4,  # Hackathons
                "per_page": 30,
                "page": page,
                "_fields": "id,link,title,content,yoast_head_json,date,modified",
            },
        )
        if not isinstance(posts, list) or not posts:
            break

        for post in posts:
            pid = post.get("id")
            if not pid or pid in seen:
                continue
            seen.add(pid)

            title = _clean_html((post.get("title") or {}).get("rendered") or "")
            url = post.get("link")
            if not title or not url:
                continue

            yoast = (post.get("yoast_head_json") or {}).get("description") or ""
            content_html = (post.get("content") or {}).get("rendered") or ""
            text = BeautifulSoup(content_html, "lxml").get_text("\n", strip=True)
            blob = f"{title}\n{yoast}\n{text}"

            mode = _detect_mode(blob)
            if mode not in {"online", "hybrid"}:
                # Keep big-company events even if mode is ambiguous (often hybrid)
                if not is_big_company(title=title):
                    continue
                mode = "hybrid"

            amount, currency, prize_text, has_reward = _extract_prize(blob)
            corporate = is_big_company(title=title)
            if not has_reward and not corporate:
                continue
            if not has_reward and corporate:
                prize_text = prize_text or "Corporate prizes / internships"
                has_reward = True

            deadline = _extract_deadline(blob)
            org = _extract_org(title, text) or ("Corporate / India" if corporate else "Internshala")

            results.append(
                Hackathon(
                    id=f"internshala-{pid}",
                    title=title,
                    url=url,
                    source="Internshala",
                    mode=mode,
                    prize_amount=amount,
                    prize_currency=currency,
                    prize_text=prize_text,
                    has_cash_prize=has_reward,
                    submission_deadline=deadline,
                    registration_deadline=deadline,
                    start_date=None,
                    end_date=deadline,
                    organization=org,
                    themes=["India", "Corporate"] if corporate else ["India"],
                    participants=None,
                    status="open",
                    location="Online" if mode == "online" else "Hybrid",
                    thumbnail=None,
                    focus="ai_product" if re.search(r"\bai\b|ml|genai|llm", blob, re.I) else None,
                )
            )

    return results


def _clean_html(value: str) -> str:
    return BeautifulSoup(value, "lxml").get_text(" ", strip=True)


def _detect_mode(blob: str) -> str:
    b = blob.lower()
    if "hybrid" in b or ("online" in b and "offline" in b):
        return "hybrid"
    if any(k in b for k in ("online", "virtual", "remote", "from anywhere")):
        return "online"
    if any(k in b for k in ("offline", "in-person", "on campus", "bengaluru finale")):
        return "hybrid" if "online" in b or "virtual" in b else "offline"
    return "unknown"


def _extract_prize(blob: str) -> tuple[float | None, str | None, str | None, bool]:
    # Prefer explicit prize-pool phrasing
    m = re.search(
        r"(?:prize pool|worth|prizes?)\s*(?:of|:)?\s*((?:₹|Rs\.?|INR|\$)\s*[0-9,]+(?:\s*(?:lakh|lac|crore|L|Cr))?)",
        blob,
        re.I,
    )
    candidate = m.group(1) if m else None
    if not candidate:
        m2 = re.search(r"((?:₹|Rs\.?|INR)\s*[0-9,]+(?:\s*(?:lakh|lac|crore))?)", blob, re.I)
        candidate = m2.group(1) if m2 else None

    if candidate:
        amount, currency, text = _parse_inr_or_usd(candidate)
        if amount and amount >= 1000:
            return amount, currency, text, True

    if re.search(r"internship|ppi|macbook|placement|stipend", blob, re.I):
        return None, "INR", "Internships / PPI / hardware", True
    return None, None, None, False


def _parse_inr_or_usd(raw: str) -> tuple[float | None, str | None, str | None]:
    text = raw.strip()
    # Normalize Indian grouping: 1,00,000 / 50,00,000 → 100000
    normalized = re.sub(r"(?<=\d),(?=\d{2}(?:,\d{2})*(?:,\d{3})?\b)", "", text)
    normalized = re.sub(r"(?<=\d),(?=\d{3}\b)", "", normalized)

    m = re.search(
        r"(?:₹|rs\.?|inr)\s*([0-9]+(?:\.[0-9]+)?)\s*(lakh|lac|crore|l|cr)?",
        normalized,
        re.I,
    )
    if m:
        val = float(m.group(1))
        unit = (m.group(2) or "").lower()
        if unit in {"lakh", "lac", "l"}:
            val *= 100_000
        elif unit in {"crore", "cr"}:
            val *= 10_000_000
        return val, "INR", f"INR {val:,.0f}"

    amount, currency, cleaned = parse_money(normalized)
    return amount, currency, cleaned


def _extract_deadline(blob: str) -> str | None:
    patterns = [
        r"registration(?:s)?\s*(?:deadline|end|closes?|last date)\s*[:\-]?\s*([^\n.]{6,60})",
        r"(?:deadline|last date|apply by|register by|registrations?\s+end)\s*[:\-]?\s*([^\n.]{6,60})",
        r"(?:ends? on|until|till)\s*([0-9]{1,2}\s+[A-Za-z]{3,9}\s+[0-9]{4}[^\n.]{0,20})",
        r"([0-9]{1,2}\s+[A-Za-z]{3,9}\s+[0-9]{4}\s*(?:at\s*[0-9]{1,2}:[0-9]{2}\s*(?:am|pm)\s*ist)?)",
    ]
    for pat in patterns:
        m = re.search(pat, blob, re.I)
        if not m:
            continue
        value = m.group(1).strip(" .")
        # Reject obvious junk
        if len(value) < 6 or "certificate" in value.lower():
            continue
        return value
    return None


def _extract_org(title: str, text: str) -> str | None:
    m = re.search(r"\bby\s+([A-Z][A-Za-z0-9& .]{2,40})", title)
    if m:
        return m.group(1).strip()
    m = re.search(r"(?:organized by|hosted by|powered by)\s+([A-Za-z0-9& .]{2,50})", text, re.I)
    if m:
        return m.group(1).strip(" .")
    return None
