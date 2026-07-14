# Hack-Search

Scrapes **online / hybrid hackathons with cash prizes**, biased toward **AI, product, and Web2** (Web3 de-emphasized).

On each refresh, only events whose **submission/registration deadline is within the next 30 days (IST)** are listed — closed and far-future events are hidden.

## Sources

| Source | Focus |
|---|---|
| [Devpost](https://devpost.com/hackathons) | Global online challenges |
| [Unstop](https://unstop.com/hackathons) | India online cash hackathons |
| [Hack2Skill](https://hack2skill.com) | AI / corporate / product events |
| [Devfolio](https://devfolio.co/hackathons) | Online events with prizes |
| [DoraHacks](https://dorahacks.io/hackathon) | AI / product virtual events (crypto-heavy ones filtered out) |
| [HackerEarth](https://www.hackerearth.com/challenges/) | Online company challenges |
| [Hack Club](https://hackathons.hackclub.com) / [MLH](https://mlh.io) / [Luma](https://lu.ma) | Extra online coverage |

## Setup

```bash
cd "hackathon scrapper"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Use day-to-day (with Refresh button)

```bash
python server.py
```

Then open **http://127.0.0.1:8765**

- Browse the list
- Click **Refresh list** anytime (days later is fine) to re-scrape live sources and reload

## One-shot scrape

```bash
python scrape.py --open
```

Outputs:

- `output/hackathons.html`
- `output/hackathons.json`

### Useful flags

```bash
# Also keep events where cash prize wasn't detected
python scrape.py --include-no-cash

# Include crypto / Web3-heavy listings
python scrape.py --include-web3

# Specific sources only
python scrape.py --sources Devpost Hack2Skill DoraHacks Unstop
```
