from __future__ import annotations

import html
import json
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
      font-size: 0.8rem;
      max-width: 280px;
      text-align: right;
      line-height: 1.45;
    }}
    #refreshStatus .refreshed-at {{
      display: block;
      margin-top: 2px;
      color: var(--text);
      font-weight: 600;
      font-variant-numeric: tabular-nums;
      letter-spacing: 0.01em;
    }}
    #refreshStatus.error {{ color: var(--danger); }}
    #refreshStatus.ok {{ color: var(--accent); }}
    #refreshStatus.ok .refreshed-at {{ color: var(--accent); }}
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
    .reminders {{
      margin-top: 16px;
      padding: 14px 16px;
      border: 1px solid var(--line);
      border-radius: 14px;
      background: linear-gradient(180deg, #17222c, #141c24);
      display: flex;
      flex-wrap: wrap;
      gap: 12px 18px;
      align-items: center;
      justify-content: space-between;
    }}
    .reminders-copy {{
      display: flex;
      flex-direction: column;
      gap: 2px;
      min-width: min(100%, 280px);
    }}
    .reminders-copy strong {{
      font-size: 0.98rem;
    }}
    .reminders-copy span {{
      color: var(--muted);
      font-size: 0.84rem;
      line-height: 1.4;
    }}
    .reminders-actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .reminders-actions button {{
      border: 1px solid var(--line);
      background: var(--panel);
      color: var(--text);
      font: inherit;
      font-weight: 600;
      font-size: 0.86rem;
      padding: 10px 14px;
      border-radius: 10px;
      cursor: pointer;
    }}
    .reminders-actions button:hover {{
      border-color: var(--accent);
    }}
    .reminders-actions button:disabled {{
      opacity: 0.55;
      cursor: not-allowed;
    }}
    #remindStatus {{
      width: 100%;
      color: var(--muted);
      font-size: 0.82rem;
    }}
    #remindStatus.ok {{ color: var(--accent); }}
    #remindStatus.error {{ color: var(--danger); }}
    .list {{ display: flex; flex-direction: column; gap: 12px; }}
    .card {{
      display: grid;
      grid-template-columns: 34px 72px 1fr auto;
      gap: 14px;
      align-items: center;
      background: linear-gradient(180deg, var(--panel), var(--panel-2));
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 16px;
      color: inherit;
      transition: transform 160ms ease, border-color 160ms ease;
    }}
    .card:hover {{
      transform: translateY(-2px);
      border-color: var(--accent);
    }}
    .card.is-reminded {{
      border-color: #2f7a4e;
      box-shadow: inset 3px 0 0 #3dd68a;
    }}
    .pick {{
      display: grid;
      place-items: center;
      cursor: pointer;
      user-select: none;
    }}
    .pick input {{
      width: 18px;
      height: 18px;
      margin: 0;
      accent-color: var(--accent);
      cursor: pointer;
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
    .title a {{
      color: inherit;
      text-decoration: none;
    }}
    .title a:hover {{
      color: var(--accent);
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
      text-align: right;
      min-width: 148px;
      line-height: 1.25;
    }}
    .deadline .label {{
      display: block;
      font-size: 0.68rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      font-weight: 600;
      color: var(--muted);
      margin-bottom: 4px;
    }}
    .deadline .date {{
      display: block;
      color: var(--text);
      font-size: 0.98rem;
      font-weight: 700;
      letter-spacing: -0.01em;
    }}
    .deadline .time {{
      display: block;
      margin-top: 2px;
      color: var(--deadline);
      font-size: 0.82rem;
      font-weight: 600;
      font-variant-numeric: tabular-nums;
    }}
    .deadline .tba {{
      color: var(--muted);
      font-size: 0.9rem;
      font-weight: 600;
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
    .prize a {{
      color: var(--muted);
      text-decoration: none;
      font-size: 0.82rem;
    }}
    .prize a:hover {{ color: var(--accent); }}
    .empty {{
      padding: 28px;
      text-align: center;
      color: var(--muted);
      border: 1px dashed var(--line);
      border-radius: 14px;
    }}
    @media (max-width: 700px) {{
      .card {{ grid-template-columns: 28px 56px 1fr; }}
      .side {{
        grid-column: 2 / -1;
        align-items: flex-start;
        text-align: left;
        min-width: 0;
      }}
      .deadline, .prize {{ text-align: left; max-width: none; }}
      .rank {{ width: 56px; height: 56px; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="topbar">
      <header>
        <h1>Hack-Search</h1>
        <p>AI, product, and Web2-focused listings from Devpost, Unstop, Internshala, Hack2Skill, TechGig, Devfolio, DoraHacks, Kaggle, and more. Click any row to open the official page.</p>
      </header>
      <div class="refresh-wrap">
        <button id="refreshBtn" type="button">Refresh list</button>
        <div id="refreshStatus">Last refreshed<span class="refreshed-at">{html.escape(_fmt_scraped(scraped_at))}</span></div>
      </div>
    </div>

    <div class="meta">
      <span id="countMeta" class="meta-count">{len(ordered)} matching events</span>
      <span class="meta-filter">Deadlines in IST · next 30 days only · earliest first</span>
    </div>

    <section class="reminders" id="remindersPanel" aria-label="Hackathon reminders">
      <div class="reminders-copy">
        <strong id="remindCount">0 reminders selected</strong>
        <span>Check hackathons below — you’ll get alerts 24h, 12h, and 3h before each deadline.</span>
      </div>
      <div class="reminders-actions">
        <button type="button" id="enableNotifBtn">Enable browser alerts</button>
        <button type="button" id="exportIcsBtn" disabled>Add to calendar</button>
      </div>
      <div id="remindStatus"></div>
    </section>

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
    const remindCount = document.getElementById('remindCount');
    const remindStatus = document.getElementById('remindStatus');
    const enableNotifBtn = document.getElementById('enableNotifBtn');
    const exportIcsBtn = document.getElementById('exportIcsBtn');
    const lastRefreshed = {json.dumps(_fmt_scraped(scraped_at))};

    const STORAGE_KEY = 'hacksearch.reminders.v1';
    const FIRED_KEY = 'hacksearch.reminders.fired.v1';
    const OFFSETS = [
      {{ key: '24h', ms: 24 * 60 * 60 * 1000, label: '24 hours' }},
      {{ key: '12h', ms: 12 * 60 * 60 * 1000, label: '12 hours' }},
      {{ key: '3h', ms: 3 * 60 * 60 * 1000, label: '3 hours' }},
    ];
    const timers = new Map();

    function showLastRefreshed() {{
      refreshStatus.className = '';
      refreshStatus.innerHTML = 'Last refreshed<span class="refreshed-at">' + lastRefreshed + '</span>';
    }}

    function loadReminders() {{
      try {{ return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{{}}'); }}
      catch {{ return {{}}; }}
    }}

    function saveReminders(map) {{
      localStorage.setItem(STORAGE_KEY, JSON.stringify(map));
    }}

    function loadFired() {{
      try {{ return JSON.parse(localStorage.getItem(FIRED_KEY) || '{{}}'); }}
      catch {{ return {{}}; }}
    }}

    function saveFired(map) {{
      localStorage.setItem(FIRED_KEY, JSON.stringify(map));
    }}

    function setRemindStatus(text, kind) {{
      remindStatus.textContent = text || '';
      remindStatus.className = kind || '';
    }}

    function cardPayload(card) {{
      return {{
        id: card.dataset.id,
        title: card.dataset.eventTitle || card.querySelector('.title')?.textContent?.trim() || 'Hackathon',
        url: card.dataset.url || '',
        deadline: card.dataset.deadline || '',
      }};
    }}

    function updateRemindUI() {{
      const map = loadReminders();
      const n = Object.keys(map).length;
      remindCount.textContent = n === 1 ? '1 reminder selected' : `${{n}} reminders selected`;
      exportIcsBtn.disabled = n === 0;
      cards.forEach(card => {{
        const on = Boolean(map[card.dataset.id]);
        const box = card.querySelector('.remind-toggle');
        if (box) box.checked = on;
        card.classList.toggle('is-reminded', on);
      }});
      if ('Notification' in window && Notification.permission === 'granted') {{
        enableNotifBtn.textContent = 'Browser alerts on';
        enableNotifBtn.disabled = true;
      }}
    }}

    function clearTimers() {{
      timers.forEach(id => clearTimeout(id));
      timers.clear();
    }}

    function fireReminder(item, offset) {{
      const fired = loadFired();
      const key = `${{item.id}}:${{offset.key}}`;
      if (fired[key]) return;
      fired[key] = Date.now();
      saveFired(fired);

      const title = `${{offset.label}} left · ${{item.title}}`;
      const body = `Deadline approaching. Open the hackathon page to submit.`;
      if ('Notification' in window && Notification.permission === 'granted') {{
        try {{
          const n = new Notification(title, {{
            body,
            tag: key,
            renotify: true,
            data: {{ url: item.url }},
          }});
          n.onclick = () => {{
            window.focus();
            if (item.url) window.open(item.url, '_blank', 'noopener');
            n.close();
          }};
        }} catch {{
          setRemindStatus(`${{title}} — ${{body}}`, 'ok');
        }}
      }} else {{
        setRemindStatus(`${{title}} — enable browser alerts to get desktop notifications.`, 'ok');
      }}
    }}

    function scheduleItem(item) {{
      const deadline = Date.parse(item.deadline);
      if (!Number.isFinite(deadline)) return;
      const now = Date.now();
      if (deadline <= now) return;

      OFFSETS.forEach(offset => {{
        const when = deadline - offset.ms;
        const key = `${{item.id}}:${{offset.key}}`;
        if (timers.has(key)) {{
          clearTimeout(timers.get(key));
          timers.delete(key);
        }}
        const fired = loadFired();
        if (fired[key]) return;

        // Already in the reminder window (late check / page just opened)
        if (when <= now && now < deadline) {{
          fireReminder(item, offset);
          return;
        }}
        if (when <= now) return;

        const wait = when - now;
        // setTimeout is unreliable beyond ~24 days; poller covers those
        if (wait > 24 * 60 * 60 * 1000) return;
        const tid = setTimeout(() => fireReminder(item, offset), wait);
        timers.set(key, tid);
      }});
    }}

    function rescheduleAll() {{
      clearTimers();
      const map = loadReminders();
      Object.values(map).forEach(scheduleItem);
    }}

    async function enableNotifications() {{
      if (!('Notification' in window)) {{
        setRemindStatus('This browser does not support notifications. Use Add to calendar instead.', 'error');
        return false;
      }}
      let perm = Notification.permission;
      if (perm === 'default') perm = await Notification.requestPermission();
      if (perm !== 'granted') {{
        setRemindStatus('Notification permission blocked. You can still use Add to calendar.', 'error');
        return false;
      }}
      updateRemindUI();
      rescheduleAll();
      setRemindStatus('Browser alerts enabled for checked hackathons (24h / 12h / 3h). Keep this tab available when possible.', 'ok');
      return true;
    }}

    function toggleReminder(card, checked) {{
      const map = loadReminders();
      const payload = cardPayload(card);
      if (!payload.id || !payload.deadline || payload.deadline.startsWith('9999')) {{
        setRemindStatus('This hackathon has no usable deadline for reminders.', 'error');
        card.querySelector('.remind-toggle').checked = false;
        return;
      }}
      if (checked) {{
        map[payload.id] = payload;
        saveReminders(map);
        updateRemindUI();
        scheduleItem(payload);
        if ('Notification' in window && Notification.permission !== 'granted') {{
          setRemindStatus('Saved. Click “Enable browser alerts” (or Add to calendar) so you actually get the 24h / 12h / 3h reminders.', 'ok');
        }} else {{
          setRemindStatus(`Reminders set for “${{payload.title}}” — 24h, 12h, and 3h before deadline.`, 'ok');
        }}
      }} else {{
        delete map[payload.id];
        saveReminders(map);
        const fired = loadFired();
        OFFSETS.forEach(o => {{ delete fired[`${{payload.id}}:${{o.key}}`]; }});
        saveFired(fired);
        updateRemindUI();
        rescheduleAll();
        setRemindStatus(`Removed reminders for “${{payload.title}}”.`, '');
      }}
    }}

    function icsEscape(text) {{
      return String(text || '')
        .replace(/\\\\/g, '\\\\\\\\')
        .replace(/;/g, '\\\\;')
        .replace(/,/g, '\\\\,')
        .replace(/\\n/g, '\\\\n');
    }}

    function toIcsUtc(iso) {{
      const d = new Date(iso);
      const p = n => String(n).padStart(2, '0');
      return (
        d.getUTCFullYear() +
        p(d.getUTCMonth() + 1) +
        p(d.getUTCDate()) +
        'T' +
        p(d.getUTCHours()) +
        p(d.getUTCMinutes()) +
        p(d.getUTCSeconds()) +
        'Z'
      );
    }}

    function exportCalendar() {{
      const map = loadReminders();
      const items = Object.values(map);
      if (!items.length) return;
      const stamp = toIcsUtc(new Date().toISOString());
      const events = items.map((item, idx) => {{
        const end = toIcsUtc(item.deadline);
        const startDate = new Date(Date.parse(item.deadline) - 60 * 60 * 1000);
        const start = toIcsUtc(startDate.toISOString());
        const uid = `${{item.id || idx}}@hack-search`;
        return [
          'BEGIN:VEVENT',
          `UID:${{uid}}`,
          `DTSTAMP:${{stamp}}`,
          `DTSTART:${{start}}`,
          `DTEND:${{end}}`,
          `SUMMARY:${{icsEscape(item.title + ' deadline')}}`,
          `DESCRIPTION:${{icsEscape('Hack-Search reminder. Submit before the deadline. ' + (item.url || ''))}}`,
          item.url ? `URL:${{item.url}}` : '',
          'BEGIN:VALARM',
          'TRIGGER:-PT24H',
          'ACTION:DISPLAY',
          `DESCRIPTION:${{icsEscape('24 hours left: ' + item.title)}}`,
          'END:VALARM',
          'BEGIN:VALARM',
          'TRIGGER:-PT12H',
          'ACTION:DISPLAY',
          `DESCRIPTION:${{icsEscape('12 hours left: ' + item.title)}}`,
          'END:VALARM',
          'BEGIN:VALARM',
          'TRIGGER:-PT3H',
          'ACTION:DISPLAY',
          `DESCRIPTION:${{icsEscape('3 hours left: ' + item.title)}}`,
          'END:VALARM',
          'END:VEVENT',
        ].filter(Boolean).join('\\r\\n');
      }});
      const ics = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//Hack-Search//Reminders//EN',
        'CALSCALE:GREGORIAN',
        'METHOD:PUBLISH',
        ...events,
        'END:VCALENDAR',
      ].join('\\r\\n');
      const blob = new Blob([ics], {{ type: 'text/calendar;charset=utf-8' }});
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'hack-search-reminders.ics';
      a.click();
      URL.revokeObjectURL(a.href);
      setRemindStatus('Calendar file downloaded — import it into Google/Apple/Outlook for reliable 24h / 12h / 3h alerts.', 'ok');
    }}

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

    cards.forEach(card => {{
      const box = card.querySelector('.remind-toggle');
      if (!box) return;
      box.addEventListener('click', e => e.stopPropagation());
      box.addEventListener('change', async () => {{
        if (box.checked && 'Notification' in window && Notification.permission === 'default') {{
          await enableNotifications();
        }}
        toggleReminder(card, box.checked);
      }});
    }});

    enableNotifBtn.addEventListener('click', enableNotifications);
    exportIcsBtn.addEventListener('click', exportCalendar);

    async function refresh() {{
      refreshBtn.disabled = true;
      refreshStatus.className = '';
      refreshStatus.textContent = 'Refreshing…';
      try {{
        const res = await fetch('/api/refresh', {{ method: 'POST' }});
        if (!res.ok) throw new Error('Refresh failed (' + res.status + ')');
        const data = await res.json();
        refreshStatus.className = 'ok';
        refreshStatus.textContent = `Done — ${{data.total_filtered}} events. Reloading…`;
        setTimeout(() => window.location.reload(), 600);
      }} catch (err) {{
        refreshStatus.className = '';
        refreshStatus.textContent = 'Opening GitHub Actions…';
        window.open(
          'https://github.com/skx56/Hack-Search/actions/workflows/deploy.yml',
          '_blank',
          'noopener'
        );
        setTimeout(showLastRefreshed, 1500);
      }} finally {{
        refreshBtn.disabled = false;
      }}
    }}

    refreshBtn.addEventListener('click', refresh);
    showLastRefreshed();
    updateRemindUI();
    rescheduleAll();
    setInterval(rescheduleAll, 60 * 1000);
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
    deadline_html = format_deadline_markup(deadline_dt)
    deadline_label = format_deadline_ist(deadline_dt)
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

    event_id = html.escape(h.id or f"event-{index}")
    event_title = html.escape(h.title)
    event_url = html.escape(h.url)

    return f"""
    <article class="card"
       data-id="{event_id}"
       data-event-title="{event_title}"
       data-url="{event_url}"
       data-source="{html.escape(h.source)}"
       data-focus="{html.escape(focus)}"
       data-title="{html.escape(h.title.lower())}"
       data-deadline="{html.escape(deadline_sort)}"
       data-prize-sort="{prize_sort}"
       data-hay="{hay}">
      <label class="pick" title="Remind me 24h / 12h / 3h before deadline">
        <input type="checkbox" class="remind-toggle" aria-label="Remind me about {event_title}" />
      </label>
      <div class="rank">#{index}</div>
      <div>
        <h2 class="title"><a href="{event_url}" target="_blank" rel="noopener">{event_title}</a></h2>
        <div class="sub">{html.escape(org) if org else "Organizer TBA"}</div>
        <div class="chips">{''.join(chips)}</div>
      </div>
      <div class="side">
        <div class="deadline">
          <span class="label">Deadline</span>
          {deadline_html}
        </div>
        <div class="prize">
          <strong>{html.escape(prize)}</strong>
          <a href="{event_url}" target="_blank" rel="noopener">Open page →</a>
        </div>
      </div>
    </article>
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

    # DoraHacks-style: 2026/08/23 23:59
    m = re.fullmatch(r"(\d{4})/(\d{2})/(\d{2})\s+(\d{2}):(\d{2})", text)
    if m:
        y, mo, d, hh, mm = map(int, m.groups())
        return datetime(y, mo, d, hh, mm, tzinfo=timezone.utc)

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
                # Date-only → end of that day in IST
                if fmt in {"%Y-%m-%d", "%b %d, %Y", "%B %d, %Y", "%d %b %Y", "%d %B %Y"}:
                    dt = dt.replace(hour=23, minute=59, tzinfo=IST)
                else:
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


def format_deadline_ist(dt: datetime | None) -> str:
    if not dt:
        return "TBA"
    local = dt.astimezone(IST)
    return f"{_fmt_day(local)} · {_fmt_clock(local)} IST"


def format_deadline_markup(dt: datetime | None) -> str:
    if not dt:
        return '<span class="tba">TBA</span>'
    local = dt.astimezone(IST)
    return (
        f'<span class="date">{html.escape(_fmt_day(local))}</span>'
        f'<span class="time">{html.escape(_fmt_clock(local))} IST</span>'
    )


def _fmt_day(local: datetime) -> str:
    return f"{local.day} {local.strftime('%b %Y')}"


def _fmt_clock(local: datetime) -> str:
    hour = local.hour % 12 or 12
    return f"{hour}:{local.strftime('%M %p')}"


def _fmt_scraped(value: str) -> str:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(IST)
        return f"{_fmt_day(dt)}, {_fmt_clock(dt)} IST"
    except Exception:
        return value
