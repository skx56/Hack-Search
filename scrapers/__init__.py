from .devpost import scrape_devpost
from .unstop import scrape_unstop
from .devfolio import scrape_devfolio
from .hackerearth import scrape_hackerearth
from .hack2skill import scrape_hack2skill
from .dorahacks import scrape_dorahacks
from .internshala import scrape_internshala
from .techgig import scrape_techgig
from .hackclub import scrape_hackclub
from .mlh import scrape_mlh
from .luma import scrape_luma

# Default sources prioritize AI / Web2 / product hackathons + India corporate.
SCRAPERS = [
    ("Devpost", scrape_devpost),
    ("Unstop", scrape_unstop),
    ("Internshala", scrape_internshala),
    ("Hack2Skill", scrape_hack2skill),
    ("TechGig", scrape_techgig),
    ("Devfolio", scrape_devfolio),
    ("DoraHacks", scrape_dorahacks),
    ("HackerEarth", scrape_hackerearth),
    ("Hack Club", scrape_hackclub),
    ("MLH", scrape_mlh),
    ("Luma", scrape_luma),
]

__all__ = ["SCRAPERS"]
