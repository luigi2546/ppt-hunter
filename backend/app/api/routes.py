import csv
import json
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from re import findall, sub
from urllib.parse import quote, unquote, urljoin, urlparse
from zipfile import ZIP_STORED, ZipFile

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.document import Document, SearchRun
from app.schemas.documents import (
    BulkDownloadCreate,
    BulkDownloadRead,
    DocumentDetail,
    DocumentRead,
    DocumentStatsRead,
    ManualDocumentCreate,
    ManualLinksCreate,
    ManualLinksRead,
    MetadataExportRead,
    PublicPortalExportRead,
    SearchRunCreate,
    SearchRunRead,
)
from app.services.public_portal import export_public_portal as publish_public_portal
from app.services.storage import ensure_local_file, is_remote_storage_enabled, upload_export_file, upload_file
from app.services.urls import canonicalize_url, detect_file_type
from app.tasks.jobs import discover_presentations, download_document

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/search-runs", response_model=SearchRunRead)
def create_search_run(payload: SearchRunCreate, db: Session = Depends(get_db)) -> SearchRun:
    run = SearchRun(query=payload.query, provider=payload.provider, status="queued")
    db.add(run)
    db.commit()
    db.refresh(run)
    discover_presentations.delay(run.id, payload.query, payload.provider, 500, True)
    return run


@router.get("/search-runs", response_model=list[SearchRunRead])
def list_search_runs(db: Session = Depends(get_db), limit: int = Query(default=20, ge=1, le=100)) -> list[SearchRun]:
    return list(db.scalars(select(SearchRun).order_by(desc(SearchRun.created_at)).limit(limit)))


@router.get("/documents", response_model=list[DocumentRead])
def list_documents(
    db: Session = Depends(get_db),
    status: str | None = None,
    q: str | None = None,
    limit: int = Query(default=500, ge=1, le=1000),
) -> list[Document]:
    stmt = select(Document).order_by(desc(Document.created_at)).limit(limit)
    if status:
        stmt = stmt.where(Document.status == status)
    if q:
        like = f"%{q}%"
        stmt = stmt.where((Document.title.ilike(like)) | (Document.extracted_text.ilike(like)))
    return list(db.scalars(stmt))


@router.get("/documents/stats", response_model=DocumentStatsRead)
def document_stats(db: Session = Depends(get_db)) -> DocumentStatsRead:
    rows = db.execute(select(Document.status, func.count()).group_by(Document.status)).all()
    by_status = {str(status): int(count) for status, count in rows}
    total = sum(by_status.values())
    downloaded = by_status.get("downloaded", 0)
    ready = by_status.get("ready", 0)
    completed = downloaded + ready
    queued = by_status.get("download_queued", 0) + by_status.get("discovered", 0)
    downloading = by_status.get("downloading", 0)
    failed = sum(count for status, count in by_status.items() if "fail" in status)
    left = max(total - completed, 0)

    return DocumentStatsRead(
        total=total,
        downloaded=downloaded,
        ready=ready,
        completed=completed,
        left=left,
        queued=queued,
        downloading=downloading,
        failed=failed,
        by_status=by_status,
    )


@router.post("/documents", response_model=DocumentRead)
def create_manual_document(payload: ManualDocumentCreate, db: Session = Depends(get_db)) -> Document:
    url = str(payload.url)
    file_type = detect_file_type(url)
    if file_type not in {"ppt", "pptx"}:
        raise HTTPException(status_code=400, detail="Only .ppt and .pptx URLs are supported")

    canonical_url = canonicalize_url(url)
    existing = db.scalar(select(Document).where(Document.canonical_url == canonical_url))
    if existing:
        return existing

    document = Document(
        title=payload.title,
        source_url=url,
        canonical_url=canonical_url,
        provider="manual",
        file_type=file_type,
        status="discovered",
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


@router.post("/documents/manual-links", response_model=ManualLinksRead)
def create_manual_links(payload: ManualLinksCreate, db: Session = Depends(get_db)) -> ManualLinksRead:
    created = 0
    existing_count = 0
    queued = 0
    skipped = 0
    discovery_runs = 0
    invalid: list[str] = []
    documents_to_queue: list[str] = []
    seen_inputs: set[str] = set()
    seen_candidates: set[str] = set()

    for raw_url in payload.urls:
        url = normalize_input_url(raw_url)
        if not url or url in seen_inputs:
            continue
        seen_inputs.add(url)

        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            invalid.append(url)
            continue

        if is_broad_archive_url(url):
            run = SearchRun(query="presentation", provider="internet_archive", status="queued")
            db.add(run)
            db.flush()
            discover_presentations.delay(run.id, run.query, run.provider, 50, True)
            discovery_runs += 1
            continue

        candidate_urls = discover_presentation_urls(url)
        if not candidate_urls:
            invalid.append(url)
            continue

        for candidate_url in candidate_urls:
            canonical_url = canonicalize_url(candidate_url)
            if canonical_url in seen_candidates:
                continue
            seen_candidates.add(canonical_url)

            file_type = detect_file_type(candidate_url)
            if file_type not in {"ppt", "pptx"}:
                invalid.append(candidate_url)
                continue

            existing = db.scalar(select(Document).where(Document.canonical_url == canonical_url))
            if existing:
                existing_count += 1
                if existing.status in {"discovered", "download_failed"}:
                    existing.status = "download_queued"
                    documents_to_queue.append(existing.id)
                    queued += 1
                else:
                    skipped += 1
                continue

            document = Document(
                title=title_from_url(candidate_url),
                source_url=candidate_url,
                canonical_url=canonical_url,
                provider="manual",
                file_type=file_type,
                status="download_queued",
            )
            db.add(document)
            db.flush()
            documents_to_queue.append(document.id)
            created += 1
            queued += 1

    db.commit()

    for document_id in documents_to_queue:
        download_document.delay(document_id)

    return ManualLinksRead(
        created=created,
        existing=existing_count,
        queued=queued,
        skipped=skipped,
        invalid=invalid,
        discovery_runs=discovery_runs,
    )


@router.get("/documents/{document_id}", response_model=DocumentDetail)
def get_document(document_id: str, db: Session = Depends(get_db)) -> Document:
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.post("/documents/{document_id}/download", response_model=DocumentRead)
def queue_download(document_id: str, db: Session = Depends(get_db)) -> Document:
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    document.status = "download_queued"
    db.commit()
    db.refresh(document)
    download_document.delay(document.id)
    return document


@router.post("/documents/download-all", response_model=BulkDownloadRead)
def queue_all_downloads(payload: BulkDownloadCreate, db: Session = Depends(get_db)) -> BulkDownloadRead:
    eligible_statuses = ["discovered", "download_failed"]
    stmt = (
        select(Document)
        .where(Document.status.in_(eligible_statuses))
        .order_by(desc(Document.created_at))
        .limit(payload.limit)
    )
    if payload.provider:
        stmt = stmt.where(Document.provider == payload.provider)

    documents = list(db.scalars(stmt))
    total_stmt = select(Document).where(Document.status.in_(eligible_statuses))
    if payload.provider:
        total_stmt = total_stmt.where(Document.provider == payload.provider)
    total_eligible = len(list(db.scalars(total_stmt)))

    queued = 0
    for document in documents:
        document.status = "download_queued"
        queued += 1
    db.commit()

    for document in documents:
        download_document.delay(document.id)

    return BulkDownloadRead(queued=queued, skipped=max(total_eligible - queued, 0))


@router.get("/exports/documents.zip")
@router.get("/documents/export.zip")
def export_downloaded_documents(
    db: Session = Depends(get_db),
    provider: str | None = None,
    limit: int = Query(default=500, ge=1, le=500),
) -> FileResponse:
    stmt = (
        select(Document)
        .where(or_(Document.file_path.is_not(None), Document.storage_key.is_not(None)))
        .order_by(desc(Document.updated_at))
        .limit(limit)
    )
    if provider:
        stmt = stmt.where(Document.provider == provider)

    documents = []
    local_paths: dict[str, Path] = {}
    for document in db.scalars(stmt):
        local_path = ensure_local_file(document.id, document.file_type, document.file_path, document.storage_key)
        if local_path:
            documents.append(document)
            local_paths[document.id] = local_path
    if not documents:
        raise HTTPException(status_code=404, detail="No downloaded files are available to export")

    export_dir = settings.storage_dir / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    export_path = export_dir / f"ppt-hunter-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.zip"

    used_names: set[str] = set()
    with ZipFile(export_path, "w", compression=ZIP_STORED) as archive:
        for document in documents:
            source = local_paths[document.id]
            archive_name = safe_archive_name(document.title, document.id, document.file_type, used_names)
            archive.write(source, archive_name)

    upload_export_file(export_path)

    return FileResponse(
        export_path,
        media_type="application/zip",
        filename=export_path.name,
    )


@router.post("/exports/metadata", response_model=MetadataExportRead)
def export_metadata(db: Session = Depends(get_db)) -> MetadataExportRead:
    documents = list(db.scalars(select(Document).order_by(desc(Document.updated_at))))
    csv_key, json_key = write_metadata_export(documents)

    return MetadataExportRead(
        document_count=len(documents),
        csv_key=csv_key,
        json_key=json_key,
    )


@router.post("/exports/portal", response_model=PublicPortalExportRead)
def export_portal(db: Session = Depends(get_db)) -> PublicPortalExportRead:
    documents = list(db.scalars(select(Document).order_by(desc(Document.updated_at))))
    csv_key, json_key = write_metadata_export(documents)
    index_key, manifest_key = publish_public_portal(documents, csv_key, json_key)

    return PublicPortalExportRead(
        document_count=len(documents),
        index_key=index_key,
        manifest_key=manifest_key,
        csv_key=csv_key,
        json_key=json_key,
    )


def write_metadata_export(documents: list[Document]) -> tuple[str, str]:
    rows = [metadata_row(document) for document in documents]

    metadata_dir = settings.storage_dir / "metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    csv_path = metadata_dir / "documents.csv"
    json_path = metadata_dir / "documents.json"

    fieldnames = list(rows[0].keys()) if rows else metadata_fieldnames()
    with csv_path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    json_path.write_text(json.dumps(rows, indent=2, default=str), encoding="utf-8")

    csv_key = "metadata/documents.csv"
    json_key = "metadata/documents.json"
    if is_remote_storage_enabled():
        upload_file(csv_path, csv_key, "text/csv")
        upload_file(json_path, json_key, "application/json")

    return csv_key, json_key


class PresentationLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if name.lower() in {"href", "src"} and value:
                self.links.append(value)


def discover_presentation_urls(url: str) -> list[str]:
    if detect_file_type(url) in {"ppt", "pptx"}:
        return [url]

    if is_archive_url(url):
        return discover_archive_presentation_urls(url)

    try:
        response = httpx.get(
            url,
            follow_redirects=True,
            timeout=20,
            headers={"User-Agent": "ppt-hunter/0.1"},
        )
        response.raise_for_status()
    except Exception:
        return []

    page_text = response.text[:2_000_000]
    parser = PresentationLinkParser()
    try:
        parser.feed(page_text)
    except Exception:
        pass

    text_links = findall(r"""(?:https?://|/|\.{1,2}/)?[^\s"'<>]+?\.pptx?(?:\?[^\s"'<>]*)?""", page_text)
    base_url = str(response.url)
    candidates = [*parser.links, *text_links]
    discovered: list[str] = []
    seen: set[str] = set()

    for candidate in candidates:
        absolute_url = urljoin(base_url, candidate.strip().rstrip(").,;]}'\""))
        if detect_file_type(absolute_url) not in {"ppt", "pptx"}:
            continue
        canonical_url = canonicalize_url(absolute_url)
        if canonical_url in seen:
            continue
        seen.add(canonical_url)
        discovered.append(absolute_url)
        if len(discovered) >= 500:
            break

    return discovered


def is_archive_url(url: str) -> bool:
    return urlparse(url).netloc.lower().removeprefix("www.") == "archive.org"


def is_broad_archive_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.netloc.lower().removeprefix("www.") != "archive.org":
        return False
    path = parsed.path.strip("/")
    return path == "" or path in {"details", "download"}


def discover_archive_presentation_urls(url: str, limit: int = 500) -> list[str]:
    parsed = urlparse(url)
    path_parts = [part for part in parsed.path.split("/") if part]

    if len(path_parts) >= 2 and path_parts[0] in {"details", "download"}:
        return archive_file_urls_for_identifier(path_parts[1], limit)

    discovered: list[str] = []
    seen: set[str] = set()
    query = '(format:"Microsoft PowerPoint" OR format:"Microsoft Powerpoint" OR format:"PowerPoint")'

    with httpx.Client(timeout=30, follow_redirects=True) as client:
        for page in range(1, 11):
            response = client.get(
                "https://archive.org/advancedsearch.php",
                params={
                    "q": query,
                    "fl[]": ["identifier"],
                    "rows": 50,
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
                for file_url in archive_file_urls_for_identifier(identifier, limit - len(discovered), client):
                    canonical_url = canonicalize_url(file_url)
                    if canonical_url in seen:
                        continue
                    seen.add(canonical_url)
                    discovered.append(file_url)
                    if len(discovered) >= limit:
                        return discovered

    return discovered


def archive_file_urls_for_identifier(identifier: str, limit: int, client: httpx.Client | None = None) -> list[str]:
    if limit <= 0:
        return []

    own_client = client is None
    http_client = client or httpx.Client(timeout=30, follow_redirects=True)
    try:
        response = http_client.get(f"https://archive.org/metadata/{quote(identifier)}")
        response.raise_for_status()
        files = response.json().get("files", [])
    except Exception:
        return []
    finally:
        if own_client:
            http_client.close()

    urls: list[str] = []
    for file_info in files:
        file_name = file_info.get("name")
        if not file_name or detect_file_type(file_name) not in {"ppt", "pptx"}:
            continue
        urls.append(f"https://archive.org/download/{quote(identifier)}/{quote(file_name)}")
        if len(urls) >= limit:
            break
    return urls


def normalize_input_url(raw_url: str) -> str:
    url = raw_url.strip().strip("<>()[]{}'\"")
    if not url:
        return ""
    parsed = urlparse(url)
    if parsed.scheme:
        return url
    if "." in parsed.path:
        return f"https://{url}"
    return url


def metadata_fieldnames() -> list[str]:
    return [
        "id",
        "title",
        "source_url",
        "provider",
        "file_type",
        "status",
        "sha256",
        "size_bytes",
        "slide_count",
        "language",
        "category",
        "confidence",
        "summary",
        "storage_key",
        "file_path",
        "error",
        "created_at",
        "updated_at",
    ]


def metadata_row(document: Document) -> dict[str, object]:
    return {
        "id": document.id,
        "title": document.title,
        "source_url": document.source_url,
        "provider": document.provider,
        "file_type": document.file_type,
        "status": document.status,
        "sha256": document.sha256,
        "size_bytes": document.size_bytes,
        "slide_count": document.slide_count,
        "language": document.language,
        "category": document.category,
        "confidence": document.confidence,
        "summary": document.summary,
        "storage_key": document.storage_key,
        "file_path": document.file_path,
        "error": document.error,
        "created_at": document.created_at.isoformat() if document.created_at else None,
        "updated_at": document.updated_at.isoformat() if document.updated_at else None,
    }


def safe_archive_name(title: str, document_id: str, file_type: str, used_names: set[str]) -> str:
    clean_title = sub(r"[^A-Za-z0-9._ -]+", "", title).strip().replace(" ", "_")[:120]
    if not clean_title:
        clean_title = "presentation"
    base_name = f"{clean_title}_{document_id[:8]}.{file_type}"
    archive_name = base_name
    counter = 2
    while archive_name in used_names:
        archive_name = f"{clean_title}_{document_id[:8]}_{counter}.{file_type}"
        counter += 1
    used_names.add(archive_name)
    return archive_name


def title_from_url(url: str) -> str:
    path_name = unquote(Path(urlparse(url).path).name)
    clean_name = sub(r"\.(pptx?|PPTX?)$", "", path_name).replace("_", " ").replace("-", " ").strip()
    return clean_name[:500] or "Untitled presentation"
