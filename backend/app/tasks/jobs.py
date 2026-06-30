from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import func, select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.document import Document, SearchRun
from app.services.content_filters import contains_chinese_signal, is_allowed_candidate
from app.services.downloader import download_to_storage
from app.services.enrichment import categorize, summarize
from app.services.extractor import count_pptx_images, extract_document_text
from app.services.indexer import index_document
from app.services.link_crawler import crawl_page, title_from_url
from app.services.search_providers import get_provider
from app.services.storage import ensure_local_file, upload_downloaded_file
from app.services.urls import canonicalize_url
from app.tasks.celery_app import celery_app


ACTIVE_DOWNLOAD_STATUSES = {"download_queued", "downloading"}
TRANSIENT_NETWORK_ERROR_TEXT = (
    "temporary failure in name resolution",
    "name or service not known",
    "connection reset",
    "connection aborted",
    "timeout",
    "timed out",
)


@celery_app.task(name="discover_presentations")
def discover_presentations(run_id: str, query: str, provider_name: str, limit: int, auto_download: bool = False) -> None:
    with SessionLocal() as db:
        run = db.get(SearchRun, run_id)
        if not run:
            return
        run.status = "running"
        db.commit()

        try:
            provider = get_provider(provider_name)
            results = provider.search(query, limit)
            created = 0
            skipped = 0
            queued_document_ids: list[str] = []
            for result in results:
                allowed, _reason = is_allowed_candidate(result.url, result.title, result.description)
                if not allowed:
                    skipped += 1
                    continue
                canonical_url = canonicalize_url(result.url)
                existing = db.scalar(select(Document).where(Document.canonical_url == canonical_url))
                if existing:
                    skipped += 1
                    continue
                document = Document(
                    search_run_id=run.id,
                    title=result.title,
                    source_url=result.url,
                    canonical_url=canonical_url,
                    provider=result.provider,
                    file_type=result.file_type,
                    description=result.description,
                    status="download_queued" if auto_download else "discovered",
                )
                db.add(document)
                db.flush()
                if auto_download:
                    queued_document_ids.append(document.id)
                created += 1

            run.provider = provider.name
            run.status = "completed"
            run.result_count = created
            if skipped:
                run.error = f"Skipped {skipped} blocked, Chinese, or duplicate results."
            run.completed_at = datetime.utcnow()
            db.commit()

            for document_id in queued_document_ids:
                download_document.delay(document_id)
        except Exception as exc:
            run.status = "failed"
            run.error = str(exc)
            run.completed_at = datetime.utcnow()
            db.commit()


def mark_stale_downloads(db) -> int:
    stale_cutoff = datetime.utcnow() - timedelta(minutes=max(settings.archive_collection_stale_download_minutes, 5))
    stale_documents = list(
        db.scalars(
            select(Document).where(
                Document.status.in_(ACTIVE_DOWNLOAD_STATUSES),
                Document.updated_at < stale_cutoff,
            )
        )
    )
    for document in stale_documents:
        document.status = "download_failed"
        document.error = f"Marked stale so collection can continue after {settings.archive_collection_stale_download_minutes} minutes."
    if stale_documents:
        db.commit()
    return len(stale_documents)


def count_active_downloads(db) -> int:
    return db.scalar(select(func.count()).select_from(Document).where(Document.status.in_(ACTIVE_DOWNLOAD_STATUSES))) or 0


def queue_discovered_downloads(db, provider: str, limit: int, run_id: str | None = None) -> list[str]:
    if limit <= 0:
        return []

    stmt = (
        select(Document)
        .where(Document.provider == provider, Document.status == "discovered")
        .order_by(Document.created_at)
        .limit(limit)
    )
    if run_id:
        stmt = stmt.where(Document.search_run_id == run_id)

    documents = list(db.scalars(stmt))
    if not documents and run_id:
        documents = list(
            db.scalars(
                select(Document)
                .where(Document.provider == provider, Document.status == "discovered")
                .order_by(Document.created_at)
                .limit(limit)
            )
        )

    document_ids: list[str] = []
    for document in documents:
        document.status = "download_queued"
        document.error = None
        document_ids.append(document.id)

    if document_ids:
        db.commit()
    return document_ids


@celery_app.task(name="collect_archive_batches")
def collect_archive_batches(run_id: str, query: str = "presentation", start_page: int = 1, empty_batches: int = 0) -> None:
    batch_size = max(settings.archive_collection_batch_size, 1)
    target_files = max(settings.archive_collection_target_files, batch_size)
    wait_seconds = max(settings.archive_collection_wait_seconds, 10)
    pause_seconds = max(settings.archive_collection_pause_seconds, wait_seconds)
    chunk_size = max(settings.archive_collection_download_chunk_size, 1)
    max_active_downloads = max(settings.archive_collection_max_active_downloads, 1)
    max_empty_batches = max(settings.archive_collection_max_empty_batches, 1)

    with SessionLocal() as db:
        run = db.get(SearchRun, run_id)
        if not run:
            return

        run.status = "running"
        run.provider = "internet_archive"
        db.commit()

        marked_stale = mark_stale_downloads(db)
        active_downloads = count_active_downloads(db)
        if active_downloads >= max_active_downloads:
            stale_message = f" Marked {marked_stale} stale downloads." if marked_stale else ""
            run.error = (
                f"Paused: {active_downloads} active downloads. "
                f"Next check in {pause_seconds}s before scanning page {start_page}.{stale_message}"
            )
            db.commit()
            collect_archive_batches.apply_async(args=[run_id, query, start_page, empty_batches], countdown=pause_seconds)
            return

        queue_limit = min(chunk_size, max_active_downloads - active_downloads)
        queued_document_ids = queue_discovered_downloads(db, "internet_archive", queue_limit, run.id)
        if queued_document_ids:
            for document_id in queued_document_ids:
                download_document.delay(document_id)
            run.error = (
                f"Queued {len(queued_document_ids)} downloads. "
                f"Paused {pause_seconds}s before the next interval on page {start_page}."
            )
            db.commit()
            collect_archive_batches.apply_async(args=[run_id, query, start_page, empty_batches], countdown=pause_seconds)
            return

        collected_count = db.scalar(select(func.count()).select_from(Document).where(Document.provider == "internet_archive")) or 0
        if collected_count >= target_files:
            run.status = "completed"
            run.completed_at = datetime.utcnow()
            run.error = f"Target reached: {collected_count} Archive.org records."
            db.commit()
            return

        try:
            provider = get_provider("internet_archive")
            search_from_page = getattr(provider, "search_from_page")
            results, next_page, exhausted = search_from_page(query, batch_size, start_page)

            created = 0
            skipped = 0
            for result in results:
                allowed, _reason = is_allowed_candidate(result.url, result.title, result.description)
                if not allowed:
                    skipped += 1
                    continue
                canonical_url = canonicalize_url(result.url)
                existing = db.scalar(select(Document).where(Document.canonical_url == canonical_url))
                if existing:
                    skipped += 1
                    continue

                document = Document(
                    search_run_id=run.id,
                    title=result.title,
                    source_url=result.url,
                    canonical_url=canonical_url,
                    provider=result.provider,
                    file_type=result.file_type,
                    description=result.description,
                    status="discovered",
                )
                db.add(document)
                db.flush()
                created += 1

            run.result_count = (run.result_count or 0) + created
            run.completed_at = None
            if created == 0:
                empty_batches += 1
            else:
                empty_batches = 0
            run.error = (
                f"Last batch: page {start_page}, discovered {created}, skipped {skipped}, "
                f"next page {next_page}. Downloads will queue in {chunk_size}-file intervals."
            )
            db.commit()

            if exhausted or empty_batches >= max_empty_batches:
                run.status = "completed"
                run.completed_at = datetime.utcnow()
                if exhausted:
                    run.error = "Archive.org search is exhausted."
                else:
                    run.error = f"Stopped after {empty_batches} empty batches."
                db.commit()
                return

            collect_archive_batches.apply_async(args=[run_id, query, next_page, empty_batches], countdown=pause_seconds)
        except Exception as exc:
            if is_transient_network_error(exc):
                run.status = "running"
                run.error = f"Temporary network problem, retrying page {start_page}: {exc}"
                run.completed_at = None
                db.commit()
                collect_archive_batches.apply_async(args=[run_id, query, start_page, empty_batches], countdown=pause_seconds * 2)
                return

            run.status = "failed"
            run.error = str(exc)
            run.completed_at = datetime.utcnow()
            db.commit()


@celery_app.task(name="crawl_link_source")
def crawl_link_source(run_id: str, seed_url: str) -> None:
    max_pages = max(settings.link_crawl_max_pages, 1)
    max_files = max(settings.link_crawl_max_files, 1)
    max_depth = max(settings.link_crawl_max_depth, 0)
    root_host = urlparse_host(seed_url)

    if not root_host:
        return

    with SessionLocal() as db:
        run = db.get(SearchRun, run_id)
        if not run:
            return

        run.status = "running"
        run.provider = "link_crawl"
        db.commit()

        pending: list[tuple[str, int]] = [(seed_url, 0)]
        seen_pages: set[str] = set()
        seen_files: set[str] = set()
        pages_checked = 0
        created = 0
        skipped = 0
        queued_document_ids: list[str] = []

        try:
            while pending and pages_checked < max_pages and created < max_files:
                page_url, depth = pending.pop(0)
                page_canonical = canonicalize_url(page_url)
                if page_canonical in seen_pages:
                    continue
                seen_pages.add(page_canonical)
                pages_checked += 1

                page_result = crawl_page(page_url, root_host)
                for file_url in page_result.file_urls:
                    if created >= max_files:
                        break
                    canonical_url = canonicalize_url(file_url)
                    if canonical_url in seen_files:
                        skipped += 1
                        continue
                    seen_files.add(canonical_url)

                    title = title_from_url(file_url)
                    allowed, _reason = is_allowed_candidate(file_url, title)
                    if not allowed:
                        skipped += 1
                        continue

                    existing = db.scalar(select(Document).where(Document.canonical_url == canonical_url))
                    if existing:
                        skipped += 1
                        continue

                    document = Document(
                        search_run_id=run.id,
                        title=title,
                        source_url=file_url,
                        canonical_url=canonical_url,
                        provider="link_crawl",
                        file_type=Path(urlparse_path(file_url)).suffix.lower().lstrip("."),
                        status="download_queued",
                    )
                    db.add(document)
                    db.flush()
                    queued_document_ids.append(document.id)
                    created += 1

                if depth < max_depth:
                    for next_url in page_result.page_urls:
                        next_canonical = canonicalize_url(next_url)
                        if next_canonical not in seen_pages:
                            pending.append((next_url, depth + 1))

                if queued_document_ids:
                    db.commit()
                    for document_id in queued_document_ids:
                        download_document.delay(document_id)
                    queued_document_ids = []

            run.status = "completed"
            run.result_count = created
            run.completed_at = datetime.utcnow()
            run.error = f"Checked {pages_checked} pages, queued {created}, skipped {skipped}."
            db.commit()
        except Exception as exc:
            if is_transient_network_error(exc):
                run.status = "running"
                run.error = f"Temporary network problem while crawling {seed_url}: {exc}"
                run.completed_at = None
                db.commit()
                crawl_link_source.apply_async(args=[run_id, seed_url], countdown=max(settings.archive_collection_wait_seconds, 10) * 5)
                return

            run.status = "failed"
            run.error = str(exc)
            run.completed_at = datetime.utcnow()
            db.commit()


@celery_app.task(name="download_document")
def download_document(document_id: str) -> None:
    with SessionLocal() as db:
        document = db.get(Document, document_id)
        if not document:
            return
        document.status = "downloading"
        db.commit()

        try:
            path, sha256, size = download_to_storage(document.id, document.source_url, document.file_type)
            image_count = count_pptx_images(path) if document.file_type == "pptx" else None
            document.image_count = image_count
            if image_count is not None and image_count < settings.min_pptx_image_count:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
                document.status = "low_image_count"
                document.sha256 = sha256
                document.size_bytes = size
                document.file_path = None
                document.storage_key = None
                document.error = f"Skipped: {image_count} images is below minimum {settings.min_pptx_image_count}"
                db.commit()
                return
            duplicate = db.scalar(select(Document).where(Document.sha256 == sha256, Document.id != document.id))
            if duplicate:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
                document.status = "duplicate"
                document.sha256 = sha256
                document.size_bytes = size
                document.image_count = image_count
                document.file_path = None
                document.storage_key = duplicate.storage_key
                document.error = f"Duplicate of document {duplicate.id}"
                db.commit()
                return

            storage_key = upload_downloaded_file(path, document.id, document.file_type)
            document.file_path = str(path)
            document.storage_key = storage_key
            document.sha256 = sha256
            document.size_bytes = size
            document.image_count = image_count
            document.status = "downloaded"
            db.commit()
            extract_document.delay(document.id)
        except Exception as exc:
            document.status = "download_failed"
            document.error = str(exc)
            db.commit()


def is_transient_network_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(fragment in message for fragment in TRANSIENT_NETWORK_ERROR_TEXT)


def urlparse_host(url: str) -> str:
    from urllib.parse import urlparse

    return urlparse(url).netloc.lower().removeprefix("www.")


def urlparse_path(url: str) -> str:
    from urllib.parse import urlparse

    return urlparse(url).path


@celery_app.task(name="extract_document")
def extract_document(document_id: str) -> None:
    with SessionLocal() as db:
        document = db.get(Document, document_id)
        if not document or not document.file_path:
            return
        document.status = "extracting"
        db.commit()

        try:
            path = ensure_local_file(document.id, document.file_type, document.file_path, document.storage_key)
            if not path:
                raise ValueError("Downloaded file is not available in local cache or remote storage")
            document.file_path = str(path)
            text, slide_count = extract_document_text(Path(path), document.file_type)
            if contains_chinese_signal(text):
                document.extracted_text = text
                document.slide_count = slide_count
                document.status = "chinese_language"
                document.error = "Skipped: Chinese-language slide text detected"
                db.commit()
                return
            document.extracted_text = text
            document.slide_count = slide_count
            document.status = "extracted"
            db.commit()
            enrich_document.delay(document.id)
        except Exception as exc:
            document.status = "extract_failed"
            document.error = str(exc)
            db.commit()


@celery_app.task(name="enrich_document")
def enrich_document(document_id: str) -> None:
    with SessionLocal() as db:
        document = db.get(Document, document_id)
        if not document:
            return
        document.status = "enriching"
        db.commit()

        try:
            category, confidence = categorize(document.extracted_text or "", document.title)
            document.category = category
            document.confidence = confidence
            document.summary = summarize(document.extracted_text or "", document.title)
            document.status = "ready"
            db.commit()
            index_document(document)
        except Exception as exc:
            document.status = "enrich_failed"
            document.error = str(exc)
            db.commit()
