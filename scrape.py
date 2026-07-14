#!/usr/bin/env python3
"""Scrape online cash-prize hackathons from major platforms."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from scrapers import SCRAPERS
from scrapers.focus import classify_focus
from scrapers.models import Hackathon
from scrapers.report import write_html_report


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "output"


def run_all(sources: list[str] | None = None) -> list[Hackathon]:
    wanted = None
    if sources:
        wanted = {s.lower().replace(" ", "").replace("-", "") for s in sources}

    all_items: list[Hackathon] = []
    for name, fn in SCRAPERS:
        key = name.lower().replace(" ", "").replace("-", "")
        if wanted is not None and key not in wanted:
            continue
        print(f"→ Scraping {name}...")
        try:
            items = fn()
            print(f"  {len(items)} found")
            all_items.extend(items)
        except Exception as exc:  # noqa: BLE001 - keep other sources running
            print(f"  ! {name} failed: {exc}", file=sys.stderr)
    return all_items


def filter_hackathons(
    items: list[Hackathon],
    *,
    online_only: bool = True,
    cash_only: bool = True,
    min_prize: float = 0,
    exclude_web3: bool = True,
    within_days: int = 30,
) -> list[Hackathon]:
    from scrapers.report import IST, parse_deadline

    now = datetime.now(IST)
    window_end = now + timedelta(days=within_days)

    out: list[Hackathon] = []
    for h in items:
        h.focus = classify_focus(h.title, h.themes, h.source)
        if online_only and h.mode not in {"online", "hybrid"}:
            continue
        if cash_only and not h.has_cash_prize:
            continue
        if min_prize and (h.prize_amount or 0) < min_prize:
            continue
        if exclude_web3 and h.focus == "web3":
            continue

        raw = h.registration_deadline or h.submission_deadline or h.end_date
        deadline = parse_deadline(raw)
        # Only keep open hackathons whose deadline falls within the next N days
        if deadline is None:
            continue
        local_deadline = deadline.astimezone(IST)
        if local_deadline < now or local_deadline > window_end:
            continue

        out.append(h)

    def sort_key(h: Hackathon):
        raw = h.registration_deadline or h.submission_deadline or h.end_date
        dt = parse_deadline(raw)
        if dt is None:
            deadline_key = datetime(9999, 12, 31, tzinfo=timezone.utc)
        else:
            deadline_key = dt.astimezone(timezone.utc)
        return (deadline_key, h.title.lower())

    out.sort(key=sort_key)
    return out


def dedupe(items: list[Hackathon]) -> list[Hackathon]:
    seen: set[str] = set()
    unique: list[Hackathon] = []
    for h in items:
        key = (h.url or "").rstrip("/").lower()
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(h)
    return unique


def run_scrape(
    *,
    sources: list[str] | None = None,
    include_no_cash: bool = False,
    min_prize: float = 0,
    exclude_web3: bool = True,
) -> dict[str, Any]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    raw = dedupe(run_all(sources))
    filtered = filter_hackathons(
        raw,
        online_only=True,
        cash_only=not include_no_cash,
        min_prize=min_prize,
        exclude_web3=exclude_web3,
        within_days=30,
    )

    payload = {
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "total_raw": len(raw),
        "total_filtered": len(filtered),
        "filters": {
            "online_only": True,
            "cash_only": not include_no_cash,
            "min_prize": min_prize,
            "exclude_web3": exclude_web3,
            "within_days": 30,
            "deadline_window": "next_30_days_ist",
        },
        "sources": [name for name, _ in SCRAPERS],
        "hackathons": [h.to_dict() for h in filtered],
    }

    json_path = OUTPUT_DIR / "hackathons.json"
    html_path = OUTPUT_DIR / "hackathons.html"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_html_report(filtered, html_path, scraped_at=payload["scraped_at"])
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape online cash-prize hackathons")
    parser.add_argument(
        "--sources",
        nargs="*",
        help="Optional subset: Devpost Unstop Hack2Skill Devfolio DoraHacks HackerEarth ...",
    )
    parser.add_argument("--include-no-cash", action="store_true", help="Include online events without detected cash prizes")
    parser.add_argument("--include-web3", action="store_true", help="Keep crypto/Web3-heavy listings")
    parser.add_argument("--min-prize", type=float, default=0, help="Minimum prize amount (raw, per currency)")
    parser.add_argument("--open", action="store_true", help="Open the HTML report after scraping")
    args = parser.parse_args()

    payload = run_scrape(
        sources=args.sources,
        include_no_cash=args.include_no_cash,
        min_prize=args.min_prize,
        exclude_web3=not args.include_web3,
    )
    filtered = payload["hackathons"]

    print()
    print(f"Saved {payload['total_filtered']} hackathons → {OUTPUT_DIR / 'hackathons.json'}")
    print(f"Open the list → {OUTPUT_DIR / 'hackathons.html'}")
    print("For refresh button in the UI, run: python server.py")

    if args.open:
        import webbrowser

        webbrowser.open((OUTPUT_DIR / "hackathons.html").as_uri())

    print()
    print(f"{'#':<3} {'Prize':<16} {'Source':<12} Title")
    print("-" * 90)
    for i, h in enumerate(filtered[:25], 1):
        prize = h.get("prize_text") or "—"
        print(f"{i:<3} {str(prize)[:16]:<16} {h.get('source',''):<12} {str(h.get('title',''))[:55]}")
        print(f"    {h.get('url')}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
