from __future__ import annotations

import re
from typing import Any

import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/html, */*",
}

CURRENCY_SYMBOLS = {
    "fa-rupee": "INR",
    "fa-dollar": "USD",
    "fa-euro": "EUR",
    "fa-gbp": "GBP",
    "INR": "INR",
    "USD": "USD",
    "EUR": "EUR",
    "₹": "INR",
    "$": "USD",
}


def http_get(url: str, *, params: dict | None = None, timeout: int = 30) -> requests.Response:
    resp = requests.get(url, headers=HEADERS, params=params, timeout=timeout)
    resp.raise_for_status()
    return resp


def http_get_json(url: str, *, params: dict | None = None, timeout: int = 30) -> Any:
    return http_get(url, params=params, timeout=timeout).json()


def parse_money(text: str | None) -> tuple[float | None, str | None, str | None]:
    """Return (amount, currency, cleaned_text)."""
    if not text:
        return None, None, None
    cleaned = re.sub(r"<[^>]+>", "", str(text))
    cleaned = cleaned.replace("\xa0", " ").strip()
    cleaned = re.sub(r"\s+", " ", cleaned)

    currency = None
    if "₹" in cleaned or "INR" in cleaned.upper() or "Rs" in cleaned:
        currency = "INR"
    elif "€" in cleaned or "EUR" in cleaned.upper():
        currency = "EUR"
    elif "£" in cleaned or "GBP" in cleaned.upper():
        currency = "GBP"
    elif "$" in cleaned or "USD" in cleaned.upper():
        currency = "USD"

    # Normalize Indian grouping like 4,00,000 → 400000
    indian = re.sub(r"(?<=\d),(?=\d{2}(?:,\d{2})*(?:,\d{3})?\b)", "", cleaned)
    # Also strip remaining thousands separators
    compact = re.sub(r"(?<=\d),(?=\d{3}\b)", "", indian)

    m = re.search(
        r"(?:\$|₹|€|£)?\s*([0-9]+(?:\.[0-9]+)?)\s*([kKmM])?",
        compact,
    )
    amount = None
    if m:
        val = float(m.group(1))
        suf = (m.group(2) or "").lower()
        if suf == "k":
            val *= 1_000
        elif suf == "m":
            val *= 1_000_000
        amount = val

    return amount, currency, cleaned


def normalize_mode(value: str | None, *, default: str = "unknown") -> str:
    if not value:
        return default
    v = value.lower().strip()
    if v in {"online", "virtual", "digital", "remote"}:
        return "online"
    if v in {"offline", "in-person", "in person", "onsite"}:
        return "offline"
    if v in {"hybrid", "both"}:
        return "hybrid"
    if "online" in v and ("offline" in v or "in-person" in v or "hybrid" in v):
        return "hybrid"
    if "online" in v or "virtual" in v:
        return "online"
    if "offline" in v or "in-person" in v:
        return "offline"
    return default
