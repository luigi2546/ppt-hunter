from urllib.parse import parse_qsl, unquote, urlencode, urlparse, urlunparse


def canonicalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in {"fbclid", "gclid"}
    ]
    normalized = parsed._replace(
        scheme=parsed.scheme.lower() or "https",
        netloc=parsed.netloc.lower(),
        fragment="",
        query=urlencode(query, doseq=True),
    )
    return urlunparse(normalized)


def detect_file_type(url: str) -> str:
    parsed = urlparse(unquote(url.lower()))
    searchable = f"{parsed.path}?{parsed.query}"
    if ".pptx" in searchable:
        return "pptx"
    if ".ppt" in searchable:
        return "ppt"
    return "unknown"
