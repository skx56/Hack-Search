from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from .models import Hackathon

IST = ZoneInfo("Asia/Kolkata")


def write_html_report(items: list[Hackathon], path: Path, *, scraped_at: str) -> None:
    # Default order: earliest deadline first
    ordered = sorted(items, key=_deadline_sort_key)
    rows = "\n".join(_row(h, i) for i, h in enumerate(ordered, 1))
    sources = sorted({h.source for h in ordered})
    source_options = "\n".join(
        f'<option value="{html.escape(s)}">{html.escape(s)}</option>' for s in sources
    )

    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Hack-Search</title>
  <link rel="icon" type="image/png" href="logo.png" />
  <link rel="apple-touch-icon" href="logo.png" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,600;0,9..40,700;1,9..40,400&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet" />
  <style>
    :root {{
      --bg: #0f1419;
      --panel: #1a222c;
      --panel-2: #222c38;
      --text: #e8eef4;
      --muted: #93a4b5;
      --accent: #3dd6c6;
      --accent-2: #f0b429;
      --line: #2c3a49;
      --chip: #243041;
      --danger: #ff5c5c;
      --deadline: #ff9f43;
      --deadline-soft: #3a2714;
      --danger-soft: #3a1c1c;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "DM Sans", sans-serif;
      color: var(--text);
      background:
        radial-gradient(1200px 600px at 10% -10%, #1b3a3a 0%, transparent 55%),
        radial-gradient(900px 500px at 100% 0%, #3a2e14 0%, transparent 45%),
        var(--bg);
      min-height: 100vh;
    }}
    .wrap {{
      max-width: 1100px;
      margin: 0 auto;
      padding: 40px 20px 80px;
    }}
    .topbar {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: flex-start;
      flex-wrap: wrap;
    }}
    .brand {{
      display: flex;
      align-items: center;
      gap: 14px;
    }}
    .brand-logo {{
      width: 64px;
      height: 64px;
      border-radius: 14px;
      object-fit: cover;
      flex-shrink: 0;
      border: 1px solid var(--line);
      background: #000;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
    }}
    header h1 {{
      font-size: clamp(2rem, 4vw, 3rem);
      margin: 0 0 8px;
      letter-spacing: -0.03em;
      background: linear-gradient(115deg, #5eead4 0%, #60a5fa 35%, #c084fc 70%, #fb923c 100%);
      -webkit-background-clip: text;
      background-clip: text;
      color: transparent;
      -webkit-text-fill-color: transparent;
    }}
    @media (max-width: 600px) {{
      .brand-logo {{
        width: 52px;
        height: 52px;
        border-radius: 12px;
      }}
    }}
    header p {{
      margin: 0;
      color: var(--muted);
      max-width: 48rem;
      line-height: 1.5;
    }}
    .refresh-wrap {{
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      gap: 8px;
    }}
    #refreshBtn {{
      border: 1px solid var(--accent);
      background: linear-gradient(180deg, #1b3d3a, #152a2f);
      color: var(--text);
      font: inherit;
      font-weight: 700;
      padding: 12px 18px;
      border-radius: 12px;
      cursor: pointer;
      min-width: 160px;
    }}
    #refreshBtn:disabled {{
      opacity: 0.6;
      cursor: wait;
    }}
    #refreshStatus {{
      color: var(--muted);
      font-size: 0.85rem;
      max-width: 260px;
      text-align: right;
    }}
    #refreshStatus.error {{ color: var(--danger); }}
    #refreshStatus.ok {{ color: var(--accent); }}
    .meta {{
      margin-top: 18px;
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      font-size: 0.92rem;
    }}
    .meta span {{
      border-radius: 8px;
      padding: 6px 10px;
      border: 1px solid;
      font-weight: 600;
    }}
    .meta-count {{
      color: #86efac;
      background: #173528;
      border-color: #2f7a4e;
    }}
    .meta-scraped {{
      color: #c4b5fd;
      background: #2a1f3d;
      border-color: #6b4ea3;
    }}
    .meta-filter {{
      color: #ffb86b;
      background: #3a2714;
      border-color: #9a5a20;
    }}
    .controls {{
      margin: 28px 0 18px;
      display: grid;
      grid-template-columns: 1.3fr 0.7fr 0.7fr 0.7fr;
      gap: 12px;
    }}
    @media (max-width: 900px) {{
      .controls {{ grid-template-columns: 1fr 1fr; }}
    }}
    @media (max-width: 600px) {{
      .controls {{ grid-template-columns: 1fr; }}
      .refresh-wrap {{ align-items: stretch; width: 100%; }}
      #refreshStatus {{ text-align: left; max-width: none; }}
    }}
    input, select {{
      width: 100%;
      background: var(--panel);
      color: var(--text);
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 12px 14px;
      font: inherit;
      outline: none;
    }}
    input:focus, select:focus {{ border-color: var(--accent); }}
    .list {{ display: flex; flex-direction: column; gap: 12px; }}
    .card {{
      display: grid;
      grid-template-columns: 72px 1fr auto;
      gap: 16px;
      align-items: center;
      background: linear-gradient(180deg, var(--panel), var(--panel-2));
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 16px;
      text-decoration: none;
      color: inherit;
      transition: transform 160ms ease, border-color 160ms ease;
    }}
    .card:hover {{
      transform: translateY(-2px);
      border-color: var(--accent);
    }}
    .rank {{
      width: 72px;
      height: 72px;
      border-radius: 12px;
      display: grid;
      place-items: center;
      font-family: "JetBrains Mono", monospace;
      font-weight: 600;
      background: #122029;
      color: var(--accent);
      border: 1px solid var(--line);
    }}
    .title {{
      font-size: 1.08rem;
      font-weight: 700;
      margin: 0 0 6px;
      letter-spacing: -0.01em;
    }}
    .sub {{
      color: var(--muted);
      font-size: 0.92rem;
      line-height: 1.45;
    }}
    .chips {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-top: 10px;
    }}
    .chip {{
      font-size: 0.78rem;
      padding: 4px 8px;
      border-radius: 999px;
      background: var(--chip);
      border: 1px solid var(--line);
      color: var(--muted);
    }}
    .chip-source {{
      color: #d4b3ff;
      border-color: #6b4ea3;
      background: #2a1f3d;
    }}
    .chip-mode {{
      color: #8dffb5;
      border-color: #2f7a4e;
      background: #173528;
    }}
    .chip-focus {{
      color: #9ef0e4;
      border-color: #2a5a55;
      background: #173033;
    }}
    .chip-focus-general {{
      color: #9ec5ff;
      border-color: #3a5f8a;
      background: #1a2838;
    }}
    .chip-focus-web3 {{
      color: #ffb4e2;
      border-color: #8a3a6a;
      background: #351828;
    }}
    .chip-time {{
      color: #ffb86b;
      border-color: #9a5a20;
      background: #3a2714;
    }}
    .chip-theme {{
      color: #ffd6a5;
      border-color: #8a6a3a;
      background: #322818;
    }}
    .chip-theme-1 {{
      color: #c4b5fd;
      border-color: #6d5aa8;
      background: #2a2440;
    }}
    .chip-theme-2 {{
      color: #86efac;
      border-color: #3f8f63;
      background: #1a3226;
    }}
    .chip-theme-3 {{
      color: #fda4af;
      border-color: #8f4a55;
      background: #351f24;
    }}
    .side {{
      text-align: right;
      min-width: 168px;
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      gap: 8px;
    }}
    .deadline {{
      color: var(--deadline);
      font-family: "JetBrains Mono", monospace;
      font-size: 0.86rem;
      font-weight: 600;
      line-height: 1.35;
      background: var(--deadline-soft);
      border: 1px solid #9a5a20;
      border-radius: 10px;
      padding: 8px 10px;
      text-align: right;
      max-width: 210px;
    }}
    .deadline .label {{
      display: block;
      font-size: 0.68rem;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      opacity: 0.95;
      margin-bottom: 2px;
      font-weight: 700;
      color: #ffc078;
    }}
    .prize {{
      text-align: right;
    }}
    .prize strong {{
      display: block;
      color: var(--accent-2);
      font-family: "JetBrains Mono", monospace;
      font-size: 1rem;
      margin-bottom: 4px;
    }}
    .prize span {{
      color: var(--muted);
      font-size: 0.82rem;
    }}
    .empty {{
      padding: 28px;
      text-align: center;
      color: var(--muted);
      border: 1px dashed var(--line);
      border-radius: 14px;
    }}
    .server-hint {{
      display: none;
      margin-top: 12px;
      padding: 12px 14px;
      border-radius: 10px;
      border: 1px solid var(--line);
      background: #18212b;
      color: var(--muted);
      font-size: 0.9rem;
      line-height: 1.45;
    }}
    .server-hint code {{
      font-family: "JetBrains Mono", monospace;
      color: var(--accent);
    }}
    .server-hint a {{
      color: var(--accent);
    }}
    @media (max-width: 700px) {{
      .card {{ grid-template-columns: 56px 1fr; }}
      .side {{
        grid-column: 2;
        align-items: flex-start;
        text-align: left;
        min-width: 0;
      }}
      .deadline, .prize {{ text-align: left; max-width: none; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="topbar">
      <header>
        <div class="brand">
          <img class="brand-logo" src="logo.png" alt="Hack-Search logo" width="64" height="64" />
          <div>
            <h1>Hack-Search</h1>
            <p>AI, product, and Web2-focused listings from Devpost, Unstop, Hack2Skill, Devfolio, DoraHacks, and more. Click any row to open the official page.</p>
          </div>
        </div>
      </header>
      <div class="refresh-wrap">
        <button id="refreshBtn" type="button">Refresh list</button>
        <div id="refreshStatus">Updates prizes &amp; deadlines from live sources</div>
      </div>
    </div>

    <div class="meta">
      <span id="countMeta" class="meta-count">{len(ordered)} matching events</span>
      <span id="scrapedMeta" class="meta-scraped">Scraped {_fmt_scraped(scraped_at)}</span>
      <span class="meta-filter">Deadlines in IST · next 30 days only · earliest first</span>
    </div>
    <div id="serverHint" class="server-hint">
      Free hosted mode: this site auto-updates daily via GitHub Actions.
      For an on-demand refresh, open
      <a href="https://github.com/skx56/Hack-Search/actions/workflows/deploy.yml" target="_blank" rel="noopener">Actions → Deploy Hack-Search</a>
      and click <strong>Run workflow</strong>. Or locally run <code>python server.py</code>.
    </div>

    <div class="controls">
      <input id="q" type="search" placeholder="Search title, org, theme..." />
      <select id="source">
        <option value="">All sources</option>
        {source_options}
      </select>
      <select id="focus">
        <option value="">All focuses</option>
        <option value="ai_product">AI / Product</option>
        <option value="general">General</option>
        <option value="web3">Web3</option>
      </select>
      <select id="sort">
        <option value="deadline" selected>Sort by deadline</option>
        <option value="prize">Sort by prize</option>
        <option value="title">Sort by title</option>
      </select>
    </div>

    <div class="list" id="list">
      {rows if rows else '<div class="empty">No hackathons matched. Re-run with --include-no-cash.</div>'}
    </div>
  </div>

  <script>
    const cards = [...document.querySelectorAll('.card')];
    const q = document.getElementById('q');
    const source = document.getElementById('source');
    const focus = document.getElementById('focus');
    const sort = document.getElementById('sort');
    const list = document.getElementById('list');
    const refreshBtn = document.getElementById('refreshBtn');
    const refreshStatus = document.getElementById('refreshStatus');
    const serverHint = document.getElementById('serverHint');

    function apply() {{
      const query = q.value.trim().toLowerCase();
      const src = source.value;
      const foc = focus.value;
      let visible = cards.filter(card => {{
        const hay = card.dataset.hay || '';
        const okQ = !query || hay.includes(query);
        const okS = !src || card.dataset.source === src;
        const okF = !foc || card.dataset.focus === foc;
        card.style.display = okQ && okS && okF ? '' : 'none';
        return okQ && okS && okF;
      }});

      visible.sort((a, b) => {{
        if (sort.value === 'title') return a.dataset.title.localeCompare(b.dataset.title);
        if (sort.value === 'deadline') return (a.dataset.deadline || '9999').localeCompare(b.dataset.deadline || '9999');
        return Number(b.dataset.prizeSort || 0) - Number(a.dataset.prizeSort || 0);
      }});
      visible.forEach(card => list.appendChild(card));
    }}

    q.addEventListener('input', apply);
    source.addEventListener('change', apply);
    focus.addEventListener('change', apply);
    sort.addEventListener('change', apply);

    async function refresh() {{
      refreshBtn.disabled = true;
      refreshStatus.className = '';
      refreshStatus.textContent = 'Refreshing from live sources… this can take up to a minute';
      serverHint.style.display = 'none';
      try {{
        const res = await fetch('/api/refresh', {{ method: 'POST' }});
        if (!res.ok) throw new Error('Refresh failed (' + res.status + ')');
        const data = await res.json();
        refreshStatus.className = 'ok';
        refreshStatus.textContent = `Done — ${{data.total_filtered}} events. Reloading…`;
        setTimeout(() => window.location.reload(), 600);
      }} catch (err) {{
        // Static / GitHub Pages mode — open Actions for a free manual refresh
        refreshStatus.className = '';
        refreshStatus.textContent = 'Opening GitHub Actions for a free refresh…';
        serverHint.style.display = 'block';
        window.open(
          'https://github.com/skx56/Hack-Search/actions/workflows/deploy.yml',
          '_blank',
          'noopener'
        );
      }} finally {{
        refreshBtn.disabled = false;
      }}
    }}

    refreshBtn.addEventListener('click', refresh);

    fetch('/api/health').then(r => {{
      if (!r.ok) throw new Error('no');
      refreshStatus.textContent = 'Server connected — click Refresh anytime';
      refreshStatus.className = 'ok';
    }}).catch(() => {{
      refreshStatus.textContent = 'Live site · auto-updates daily · Refresh opens Actions';
      serverHint.style.display = 'block';
    }});
  </script>
</body>
</html>
"""
    path.write_text(doc, encoding="utf-8")


def _row(h: Hackathon, index: int) -> str:
    prize = h.prize_text or (
        f"{h.prize_currency} {h.prize_amount:,.0f}" if h.prize_amount else "Cash prize"
    )
    raw_deadline = h.registration_deadline or h.submission_deadline or h.end_date
    deadline_dt = parse_deadline(raw_deadline)
    deadline_label = format_deadline_ist(deadline_dt, fallback=raw_deadline)
    deadline_sort = deadline_dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if deadline_dt else "9999-12-31T23:59:59Z"

    themes_list = [t for t in (h.themes or []) if t][:3]
    org = h.organization or ""
    focus = h.focus or "general"
    focus_label = {
        "ai_product": "AI / Product",
        "web3": "Web3",
        "general": "General",
    }.get(focus, focus)
    focus_class = {
        "ai_product": "chip-focus",
        "web3": "chip-focus-web3",
        "general": "chip-focus-general",
    }.get(focus, "chip-focus-general")
    hay = html.escape(
        f"{h.title} {org} {h.source} {' '.join(themes_list)} {prize} {focus_label} {deadline_label}".lower()
    )
    prize_sort = h.prize_amount or 0
    if (h.prize_currency or "").upper() == "INR":
        prize_sort = prize_sort / 83.0

    theme_classes = ["chip-theme", "chip-theme-1", "chip-theme-2", "chip-theme-3"]
    chips = [
        f'<span class="chip chip-source">{html.escape(h.source)}</span>',
        f'<span class="chip chip-mode">{"Hybrid" if h.mode == "hybrid" else "Online"}</span>',
        f'<span class="chip {focus_class}">{html.escape(focus_label)}</span>',
    ]
    if h.time_left:
        chips.append(f'<span class="chip chip-time">{html.escape(h.time_left)}</span>')
    for i, theme in enumerate(themes_list):
        chips.append(
            f'<span class="chip {theme_classes[i % len(theme_classes)]}">{html.escape(theme)}</span>'
        )

    return f"""
    <a class="card" href="{html.escape(h.url)}" target="_blank" rel="noopener"
       data-source="{html.escape(h.source)}"
       data-focus="{html.escape(focus)}"
       data-title="{html.escape(h.title.lower())}"
       data-deadline="{html.escape(deadline_sort)}"
       data-prize-sort="{prize_sort}"
       data-hay="{hay}">
      <div class="rank">#{index}</div>
      <div>
        <h2 class="title">{html.escape(h.title)}</h2>
        <div class="sub">{html.escape(org) if org else "Organizer TBA"}</div>
        <div class="chips">{''.join(chips)}</div>
      </div>
      <div class="side">
        <div class="deadline">
          <span class="label">Deadline (IST)</span>
          {html.escape(deadline_label)}
        </div>
        <div class="prize">
          <strong>{html.escape(prize)}</strong>
          <span>Open page →</span>
        </div>
      </div>
    </a>
    """


def _deadline_sort_key(h: Hackathon):
    raw = h.registration_deadline or h.submission_deadline or h.end_date
    dt = parse_deadline(raw)
    if not dt:
        return datetime(9999, 12, 31, tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def parse_deadline(value: str | None) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if not text or text == "—":
        return None

    # ISO / offset timestamps
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        pass

    # "2026-07-15 23:59:00+05:30" already handled; try common loose forms
    for fmt in (
        "%Y-%m-%d %H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%b %d, %Y",
        "%B %d, %Y",
        "%d %b %Y",
        "%d %B %Y",
    ):
        try:
            dt = datetime.strptime(text, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=IST)
            return dt
        except ValueError:
            continue

    # Devpost-style ranges: "May 19 - Aug 17, 2026" / "Jul 13 - 21, 2026"
    range_match = re.search(
        r"(?:([A-Za-z]+)\s+(\d{1,2})\s*[-–—]\s*)?([A-Za-z]+)?\s*(\d{1,2}),?\s*(\d{4})",
        text,
    )
    if range_match:
        start_mon, _start_day, end_mon, end_day, year = range_match.groups()
        month = end_mon or start_mon
        if month and end_day and year:
            try:
                dt = datetime.strptime(f"{month} {end_day} {year}", "%b %d %Y")
                return dt.replace(hour=23, minute=59, tzinfo=IST)
            except ValueError:
                try:
                    dt = datetime.strptime(f"{month} {end_day} {year}", "%B %d %Y")
                    return dt.replace(hour=23, minute=59, tzinfo=IST)
                except ValueError:
                    pass

    # Fallback: first recognizable date token
    m = re.search(r"([A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})", text)
    if m:
        token = m.group(1).replace(",", "")
        for fmt in ("%b %d %Y", "%B %d %Y"):
            try:
                dt = datetime.strptime(token, fmt)
                return dt.replace(hour=23, minute=59, tzinfo=IST)
            except ValueError:
                continue

    return None


def format_deadline_ist(dt: datetime | None, *, fallback: str | None = None) -> str:
    if not dt:
        return "Deadline TBA" if not fallback else str(fallback)
    local = dt.astimezone(IST)
    return local.strftime("%d %b %Y, %I:%M %p IST")


def _fmt_scraped(value: str) -> str:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(IST)
        return dt.strftime("%d %b %Y, %I:%M %p IST")
    except Exception:
        return value
