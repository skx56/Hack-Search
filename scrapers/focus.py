from __future__ import annotations

"""Lightweight helpers to bias toward AI / product / Web2 hackathons."""

WEB3_ONLY_HINTS = (
    "web3",
    "blockchain",
    "crypto",
    "ethereum",
    "solidity",
    "defi",
    "nft",
    "onchain",
    "zk ",
    "zk-",
    "token gate",
    "ethglobal",
)

AI_PRODUCT_HINTS = (
    "ai",
    "machine learning",
    "llm",
    "genai",
    "generative",
    "agent",
    "ml ",
    "product",
    "saas",
    "fintech",
    "health",
    "productivity",
    "devops",
    "web",
    "mobile",
    "iot",
    "design",
    "open ended",
    "beginner friendly",
    "social good",
    "education",
    "cybersecurity",
)


def classify_focus(title: str, themes: list[str] | None = None, source: str | None = None) -> str:
    """Return 'ai_product', 'web3', or 'general'."""
    blob = f"{title} {' '.join(themes or [])} {source or ''}".lower()
    web3 = sum(1 for k in WEB3_ONLY_HINTS if k in blob)
    ai = sum(1 for k in AI_PRODUCT_HINTS if k in blob)
    if web3 >= 2 and web3 > ai:
        return "web3"
    if ai >= 1:
        return "ai_product"
    if web3 >= 1:
        return "web3"
    return "general"
