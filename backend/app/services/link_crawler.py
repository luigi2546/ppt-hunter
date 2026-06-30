from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from re import findall, sub
from urllib.parse import unquote, urldefrag, urljoin, urlparse

import httpx

from app.services.urls import canonicalize_url, detect_file_type


@dataclass(frozen=True)
class CrawlPageResult:
    file_urls: list[str]
    page_urls: list[str]


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() not in {"a", "link", "iframe", "frame"}:
            return
        for name, value in attrs:
            if name.lower() == "href" and value:
                self.links.append(value)
            if name.lower() == "src" and value:
                self.links.append(value)


def crawl_page(url: str, root_host: str) -> CrawlPageResult:
    try:
        response = httpx.get(
            url,
            follow_redirects=True,
            timeout=20,
            headers={"User-Agent": "ppt-hunter/0.1"},
        )
        response.raise_for_status()
    except Exception:
        return CrawlPageResult(file_urls=[], page_urls=[])

    content_type = response.headers.get("content-type", "").lower()
    if "text/html" not in content_type and "application/xhtml" not in content_type and not response.text.strip().startswith("<"):
        return CrawlPageResult(file_urls=[], page_urls=[])

    base_url = str(response.url)
    page_text = response.text[:2_000_000]
    parser = LinkParser()
    try:
        parser.feed(page_text)
    except Exception:
        pass

    text_links = findall(r"""(?:https?://|/|\.{1,2}/)?[^\s"'<>]+?\.pptx?(?:\?[^\s"'<>]*)?""", page_text)
    candidates = [*parser.links, *text_links]

    file_urls: list[str] = []
    page_urls: list[str] = []
    seen_files: set[str] = set()
    seen_pages: set[str] = set()

    for candidate in candidates:
        absolute_url = clean_url(urljoin(base_url, candidate))
        if not absolute_url:
            continue
        parsed = urlparse(absolute_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            continue

        file_type = detect_file_type(absolute_url)
        if file_type in {"ppt", "pptx"}:
            canonical = canonicalize_url(absolute_url)
            if canonical not in seen_files:
                seen_files.add(canonical)
                file_urls.append(absolute_url)
            continue

        if same_site(parsed.netloc, root_host) and looks_like_page(parsed.path):
            canonical = canonicalize_url(absolute_url)
            if canonical not in seen_pages:
                seen_pages.add(canonical)
                page_urls.append(absolute_url)

    return CrawlPageResult(file_urls=file_urls, page_urls=page_urls)


def clean_url(url: str) -> str:
    clean, _fragment = urldefrag(url.strip().rstrip(").,;]}'\""))
    return clean


def same_site(host: str, root_host: str) -> bool:
    host = host.lower().removeprefix("www.")
    root_host = root_host.lower().removeprefix("www.")
    return host == root_host or host.endswith(f".{root_host}")


def looks_like_page(path: str) -> bool:
    suffix = Path(urlparse(path).path).suffix.lower()
    if suffix in {"", ".html", ".htm", ".php", ".asp", ".aspx", ".jsp"}:
        return True
    return False


def title_from_url(url: str) -> str:
    path_name = unquote(Path(urlparse(url).path).name)
    clean_name = sub(r"\.(pptx?|PPTX?)$", "", path_name).replace("_", " ").replace("-", " ").strip()
    return clean_name[:500] or urlparse(url).netloc or "Untitled presentation"
