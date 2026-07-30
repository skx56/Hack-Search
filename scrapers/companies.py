"""India / global company brands that often host campus hackathons."""

BIG_COMPANY_KEYWORDS = (
    "amazon",
    "flipkart",
    "google",
    "microsoft",
    "adobe",
    "walmart",
    "cisco",
    "samsung",
    "ibm",
    "oracle",
    "nvidia",
    "intel",
    "infosys",
    "tcs",
    "wipro",
    "accenture",
    "deloitte",
    "jio",
    "reliance",
    "phonepe",
    "razorpay",
    "swiggy",
    "zomato",
    "paytm",
    "atlassian",
    "uber",
    "ola",
    "snowflake",
    "unisys",
    "hackon",
    "grid",
    "sparkathon",
    "hackwithinfy",
    "codevita",
    "sih",
    "smart india",
)


def is_big_company(title: str | None = None, organization: str | None = None) -> bool:
    blob = f"{title or ''} {organization or ''}".lower()
    return any(k in blob for k in BIG_COMPANY_KEYWORDS)
