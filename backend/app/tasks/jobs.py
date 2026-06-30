from datetime import datetime
from pathlib import Path

from sqlalchemy import func, select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.document import Document, SearchRun
from app.services.downloader import download_to_storage
from app.services.enrichment import categorize, summarize
from app.services.extractor import extract_document_text
from app.services.indexer import index_document
from app.services.search_providers import get_provider
from app.services.storage import ensure_local_file, upload_downloaded_file
from app.services.urls import canonicalize_url
from app.tasks.celery_app import celery_app


ACTIVE_DOWNLOAD_STATUSES = {"download_queued", "downloading"}


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
            queued_document_ids: list[str] = []
            for result in results:
                canonical_url = canonicalize_url(result.url)
                existing = db.scalar(select(Document).where(Document.canonical_url == canonical_url))
                if existing:
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
            run.completed_at = datetime.utcnow()
            db.commit()

            for document_id in queued_document_ids:
                download_document.delay(document_id)
        except Exception as exc:
            run.status = "failed"
            run.error = str(exc)
            run.completed_at = datetime.utcnow()
            db.commit()


@celery_app.task(name="collect_archive_batches")
def collect_archive_batches(run_id: str, query: str = "presentation", start_page: int = 1, empty_batches: int = 0) -> None:
    batch_size = max(settings.archive_collection_batch_size, 1)
    target_files = max(settings.archive_collection_target_files, batch_size)
    wait_seconds = max(settings.archive_collection_wait_seconds, 10)
    max_empty_batches = max(settings.archive_collection_max_empty_batches, 1)

    with SessionLocal() as db:
        run = db.get(SearchRun, run_id)
        if not run:
            return

        run.status = "running"
        run.provider = "internet_archive"
        db.commit()

        active_downloads = db.scalar(select(func.count()).select_from(Document).where(Document.status.in_(ACTIVE_DOWNLOAD_STATUSES))) or 0
        if active_downloads > 0:
            run.error = f"Waiting for {active_downloads} active downloads before scanning page {start_page}."
            db.commit()
            collect_archive_batches.apply_async(args=[run_id, query, start_page, empty_batches], countdown=wait_seconds)
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
            queued_document_ids: list[str] = []
            for result in results:
                canonical_url = canonicalize_url(result.url)
                existing = db.scalar(select(Document).where(Document.canonical_url == canonical_url))
                if existing:
                    continue

                document = Document(
                    search_run_id=run.id,
                    title=result.title,
                    source_url=result.url,
                    canonical_url=canonical_url,
                    provider=result.provider,
                    file_type=result.file_type,
                    description=result.description,
                    status="download_queued",
                )
                db.add(document)
                db.flush()
                queued_document_ids.append(document.id)
                created += 1

            run.result_count = (run.result_count or 0) + created
            run.completed_at = None
            if created == 0:
                empty_batches += 1
            else:
                empty_batches = 0
            run.error = f"Last batch: page {start_page}, {created} new, next page {next_page}."
            db.commit()

            for document_id in queued_document_ids:
                download_document.delay(document_id)

            if exhausted or empty_batches >= max_empty_batches:
                run.status = "completed"
                run.completed_at = datetime.utcnow()
                if exhausted:
                    run.error = "Archive.org search is exhausted."
                else:
                    run.error = f"Stopped after {empty_batches} empty batches."
                db.commit()
                return

            collect_archive_batches.apply_async(args=[run_id, query, next_page, empty_batches], countdown=wait_seconds)
        except Exception as exc:
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
            duplicate = db.scalar(select(Document).where(Document.sha256 == sha256, Document.id != document.id))
            if duplicate:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
                document.status = "duplicate"
                document.sha256 = sha256
                document.size_bytes = size
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
            document.status = "downloaded"
            db.commit()
            extract_document.delay(document.id)
        except Exception as exc:
            document.status = "download_failed"
            document.error = str(exc)
            db.commit()


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
