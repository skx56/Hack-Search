from __future__ import annotations

import html as html_lib
import re
from urllib.parse import unquote

from .models import Hackathon
from .utils import http_get


def scrape_mlh() -> list[Hackathon]:
    """Parse MLH season page microdata. Mostly in-person; keep digital/online only."""
    results: list[Hackathon] = []
    seen: set[str] = set()

    for season_url in (
        "https://mlh.io/seasons/2026/events",
        "https://mlh.io/seasons/2025/events",
    ):
        try:
            page = http_get(season_url, timeout=30).text
        except Exception:
            continue

        chunks = re.split(r'itemType="https://schema\.org/Event"', page)[1:]
        for chunk in chunks:
            url_m = re.search(r'href="(https?://[^"]+)"', chunk)
            if not url_m:
                continue
            url = html_lib.unescape(url_m.group(1)).split("?")[0]
            if url in seen:
                continue

            start = _meta(chunk, "startDate")
            end = _meta(chunk, "endDate")
            image = _meta(chunk, "image")

            place_m = re.search(
                r'itemType="https://schema\.org/Place".*?<span itemProp="name">(.*?)</span>',
                chunk,
                re.S,
            )
            location = None
            if place_m:
                location = re.sub(r"<!--.*?-->", "", place_m.group(1))
                location = re.sub(r"<[^>]+>", "", location).strip()

            # Event title is often in utm_content or nearby heading/image alt
            title = _title_from_url(url_m.group(1)) or _heading(chunk) or location or "MLH Hackathon"

            mode = "online" if _is_online(location, title, chunk) else "offline"
            if mode != "online":
                continue

            seen.add(url)
            results.append(
                Hackathon(
                    id=f"mlh-{abs(hash(url)) % 10_000_000}",
                    title=title,
                    url=url,
                    source="MLH",
                    mode="online",
                    prize_amount=None,
                    prize_currency=None,
                    prize_text=None,
                    has_cash_prize=False,
                    submission_deadline=end,
                    start_date=start,
                    end_date=end,
                    organization="Major League Hacking",
                    themes=[],
                    participants=None,
                    status="upcoming",
                    location=location or "Online",
                    thumbnail=image,
                )
            )

    return results


def _meta(chunk: str, name: str) -> str | None:
    m = re.search(rf'itemProp="{name}"[^>]*content="([^"]*)"', chunk)
    return m.group(1) if m else None


def _heading(chunk: str) -> str | None:
    m = re.search(r"<h[23][^>]*>(.*?)</h[23]>", chunk, re.S)
    if not m:
        return None
    text = re.sub(r"<[^>]+>", "", m.group(1))
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def _title_from_url(url: str) -> str | None:
    m = re.search(r"utm_content=([^&]+)", url)
    if not m:
        return None
    return unquote(m.group(1).replace("+", " ")).strip() or None


def _is_online(location: str | None, title: str | None, chunk: str) -> bool:
    blob = " ".join(x for x in [location, title, chunk[:1500]] if x).lower()
    return any(
        token in blob
        for token in ("online", "digital", "virtual", "global hack week", "everywhere")
    )
