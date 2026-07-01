from re import search
from urllib.parse import urlparse

BLOCKED_DOMAINS = {
    "walmart.com",
    "amazon.com",
    "apple.com",
    "unitedhealthgroup.com",
    "berkshirehathaway.com",
    "cvshealth.com",
    "exxonmobil.com",
    "alphabet.com",
    "google.com",
    "microsoft.com",
    "jpmorganchase.com",
    "bankofamerica.com",
    "coca-colacompany.com",
    "pepsico.com",
    "meta.com",
    "tesla.com",
    "ford.com",
    "gm.com",
    "boeing.com",
    "disney.com",
    "att.com",
    "chevron.com",
    "cigna.com",
    "comcast.com",
    "conocophillips.com",
    "deere.com",
    "delta.com",
    "fedex.com",
    "ge.com",
    "goldmansachs.com",
    "homedepot.com",
    "honeywell.com",
    "hp.com",
    "ibm.com",
    "intel.com",
    "johnsonandjohnson.com",
    "jpmorgan.com",
    "lockheedmartin.com",
    "lowes.com",
    "mckesson.com",
    "merck.com",
    "metlife.com",
    "morganstanley.com",
    "nike.com",
    "oracle.com",
    "pfizer.com",
    "proctergamble.com",
    "raytheon.com",
    "starbucks.com",
    "target.com",
    "unitedhealth.com",
    "ups.com",
    "verizon.com",
    "visa.com",
    "walgreens.com",
    "wellsfargo.com",
}

CHINESE_TERMS = {
    "china",
    "chinese",
    "mandarin",
    "中文",
    "汉语",
    "漢語",
    "中国",
    "中國",
}


def is_allowed_candidate(url: str, title: str | None = None, description: str | None = None) -> tuple[bool, str | None]:
    text = " ".join(part for part in [url, title or "", description or ""] if part).lower()
    if is_blocked_domain(url) or contains_blocked_domain(text):
        return False, "blocked_domain"
    if is_chinese_domain(url) or contains_chinese_signal(text):
        return False, "chinese"
    return True, None


def is_blocked_domain(url: str) -> bool:
    host = urlparse(url).netloc.lower().removeprefix("www.")
    if not host:
        return False
    return any(host == domain or host.endswith(f".{domain}") for domain in BLOCKED_DOMAINS)


def contains_blocked_domain(text: str) -> bool:
    return any(domain in text for domain in BLOCKED_DOMAINS)


def is_chinese_domain(url: str) -> bool:
    host = urlparse(url).netloc.lower().removeprefix("www.")
    return host.endswith(".cn") or host.endswith(".中国") or host.endswith(".中國")


def contains_chinese_signal(text: str) -> bool:
    lowered = text.lower()
    if any(term in lowered for term in CHINESE_TERMS):
        return True
    return bool(search(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]", text))
