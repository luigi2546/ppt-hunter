from datetime import datetime
from pathlib import Path

from sqlalchemy import select

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
                document.status = "duplicate"
                document.sha256 = sha256
                document.size_bytes = size
                document.file_path = str(path)
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
