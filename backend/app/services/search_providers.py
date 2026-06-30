from dataclasses import dataclass
from typing import Protocol
from urllib.parse import quote

import httpx

from app.core.config import settings
from app.services.urls import detect_file_type


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    description: str | None
    provider: str
    file_type: str


class SearchProvider(Protocol):
    name: str

    def search(self, query: str, limit: int) -> list[SearchResult]:
        ...


class MockSearchProvider:
    name = "mock"

    def search(self, query: str, limit: int) -> list[SearchResult]:
        topics = [
            "AI Strategy",
            "Cybersecurity Awareness",
            "Sales Enablement",
            "Healthcare Training",
            "Education Workshop",
        ]
        samples = []
        for index in range(limit):
            topic = topics[index % len(topics)]
            slug = topic.lower().replace(" ", "-")
            samples.append(
                (
                    f"{topic} Presentation {index + 1}",
                    f"https://example.com/public/{slug}-{index + 1}.pptx",
                    "Mock PowerPoint sample for pipeline validation.",
                )
            )
        return [
            SearchResult(title=title, url=url, description=description, provider=self.name, file_type=detect_file_type(url))
            for title, url, description in samples
        ]


class BraveSearchProvider:
    name = "brave"

    def search(self, query: str, limit: int) -> list[SearchResult]:
        if not settings.brave_search_api_key:
            return []

        enriched_query = query if "filetype:" in query or "ext:" in query else f"({query}) (filetype:ppt OR filetype:pptx)"
        results: list[SearchResult] = []
        seen_urls: set[str] = set()
        with httpx.Client(timeout=20) as client:
            for offset in range(0, limit, 20):
                response = client.get(
                    "https://api.search.brave.com/res/v1/web/search",
                    params={
                        "q": enriched_query,
                        "count": min(limit - len(results), 20),
                        "offset": offset,
                        "extra_snippets": "true",
                    },
                    headers={"X-Subscription-Token": settings.brave_search_api_key},
                )
                response.raise_for_status()
                payload = response.json()
                page_items = payload.get("web", {}).get("results", [])
                if not page_items:
                    break

                added_on_page = 0
                for item in page_items:
                    url = item.get("url")
                    if not url or url in seen_urls:
                        continue
                    seen_urls.add(url)
                    file_type = detect_file_type(url)
                    if file_type not in {"ppt", "pptx"}:
                        continue
                    results.append(
                        SearchResult(
                            title=item.get("title") or url,
                            url=url,
                            description=item.get("description"),
                            provider=self.name,
                            file_type=file_type,
                        )
                    )
                    added_on_page += 1
                    if len(results) >= limit:
                        return results
                if added_on_page == 0:
                    break
        return results


class DataForSeoProvider:
    def __init__(self, engine: str):
        self.engine = engine
        self.name = f"dataforseo_{engine}"

    def search(self, query: str, limit: int) -> list[SearchResult]:
        if not settings.dataforseo_login or not settings.dataforseo_password:
            return []

        enriched_query = query if "filetype:" in query or "ext:" in query else f"({query}) (filetype:ppt OR filetype:pptx)"
        endpoint = f"https://api.dataforseo.com/v3/serp/{self.engine}/organic/live/advanced"
        payload = [
            {
                "keyword": enriched_query,
                "location_code": 2840,
                "language_code": "en",
                "device": "desktop",
                "depth": min(limit, 500),
            }
        ]
        results: list[SearchResult] = []
        with httpx.Client(timeout=45) as client:
            response = client.post(endpoint, json=payload, auth=(settings.dataforseo_login, settings.dataforseo_password))
            response.raise_for_status()
            data = response.json()

        for task in data.get("tasks", []):
            for result_group in task.get("result", []) or []:
                for item in result_group.get("items", []) or []:
                    url = item.get("url")
                    if not url:
                        continue
                    file_type = detect_file_type(url)
                    if file_type not in {"ppt", "pptx"}:
                        continue
                    results.append(
                        SearchResult(
                            title=item.get("title") or url,
                            url=url,
                            description=item.get("description"),
                            provider=self.name,
                            file_type=file_type,
                        )
                    )
                    if len(results) >= limit:
                        return results
        return results


class InternetArchiveProvider:
    name = "internet_archive"

    def search(self, query: str, limit: int) -> list[SearchResult]:
        results: list[SearchResult] = []
        rows = 100
        search_query = f'({query}) AND (format:"Microsoft PowerPoint" OR format:"Microsoft Powerpoint" OR format:"PowerPoint")'

        with httpx.Client(timeout=30) as client:
            for page in range(1, 11):
                response = client.get(
                    "https://archive.org/advancedsearch.php",
                    params={
                        "q": search_query,
                        "fl[]": ["identifier", "title", "description"],
                        "rows": rows,
                        "page": page,
                        "output": "json",
                    },
                )
                response.raise_for_status()
                docs = response.json().get("response", {}).get("docs", [])
                if not docs:
                    break

                for item in docs:
                    identifier = item.get("identifier")
                    if not identifier:
                        continue

                    metadata_response = client.get(f"https://archive.org/metadata/{quote(identifier)}")
                    metadata_response.raise_for_status()
                    files = metadata_response.json().get("files", [])

                    for file_info in files:
                        file_name = file_info.get("name")
                        if not file_name:
                            continue
                        file_type = detect_file_type(file_name)
                        if file_type not in {"ppt", "pptx"}:
                            continue

                        results.append(
                            SearchResult(
                                title=f"{item.get('title') or identifier} - {file_name}",
                                url=f"https://archive.org/download/{quote(identifier)}/{quote(file_name)}",
                                description=normalize_description(item.get("description")),
                                provider=self.name,
                                file_type=file_type,
                            )
                        )
                        if len(results) >= limit:
                            return results

        return results


class AggregateSearchProvider:
    name = "all"

    def __init__(self, providers: list[SearchProvider]):
        self.providers = providers

    def search(self, query: str, limit: int) -> list[SearchResult]:
        results: list[SearchResult] = []
        seen_urls: set[str] = set()

        for provider in self.providers:
            try:
                provider_results = provider.search(query, limit)
            except Exception:
                continue

            for result in provider_results:
                if result.url in seen_urls:
                    continue
                seen_urls.add(result.url)
                results.append(result)
                if len(results) >= limit:
                    return results

        return results


def normalize_description(value: object) -> str | None:
    if isinstance(value, list):
        return " ".join(str(part) for part in value if part)
    if isinstance(value, str):
        return value
    return None


def get_all_providers() -> list[SearchProvider]:
    providers: list[SearchProvider] = [InternetArchiveProvider()]
    if settings.brave_search_api_key:
        providers.append(BraveSearchProvider())
    if settings.dataforseo_login and settings.dataforseo_password:
        providers.extend(
            [
                DataForSeoProvider("google"),
                DataForSeoProvider("bing"),
                DataForSeoProvider("duckduckgo"),
            ]
        )
    return providers


def get_provider(name: str) -> SearchProvider:
    if name == "all":
        return AggregateSearchProvider(get_all_providers())
    if name == "brave":
        return BraveSearchProvider()
    if name in {"internet_archive", "ia"}:
        return InternetArchiveProvider()
    if name in {"google", "bing", "duckduckgo"}:
        return DataForSeoProvider(name)
    if name == "mock":
        return MockSearchProvider()
    if name == "auto":
        if settings.brave_search_api_key:
            return BraveSearchProvider()
        if settings.dataforseo_login and settings.dataforseo_password:
            return DataForSeoProvider("google")
        return InternetArchiveProvider()
    raise ValueError(f"Unsupported provider: {name}")
