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
    title_l = (title or "").lower()
    source_l = (source or "").lower()
    blob = f"{title_l} {' '.join(themes or [])} {source_l}".lower()
    web3 = sum(1 for k in WEB3_ONLY_HINTS if k in blob)
    ai = sum(1 for k in AI_PRODUCT_HINTS if k in blob)

    # Kaggle competitions are ML / data-science by nature
    if source_l == "kaggle":
        return "ai_product"

    # Title-level AI signal wins (common on DoraHacks / mixed platforms)
    if any(k in title_l for k in ("ai ", " ai", "ai-", "ai:", "agent", "llm", "genai", "machine learning")):
        return "ai_product"
    if title_l.startswith("ai") or title_l.endswith(" ai") or " ai " in f" {title_l} ":
        return "ai_product"

    if web3 >= 2 and web3 > ai:
        return "web3"
    if ai >= 1:
        return "ai_product"
    if web3 >= 1:
        return "web3"
    return "general"
