from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Hackathon:
    id: str
    title: str
    url: str
    source: str
    mode: str  # online | offline | hybrid | unknown
    prize_amount: float | None = None
    prize_currency: str | None = None
    prize_text: str | None = None
    has_cash_prize: bool = False
    submission_deadline: str | None = None
    registration_deadline: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    organization: str | None = None
    themes: list[str] = field(default_factory=list)
    participants: int | None = None
    status: str | None = None
    location: str | None = None
    thumbnail: str | None = None
    time_left: str | None = None
    focus: str | None = None  # ai_product | web3 | general

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
