from elasticsearch import Elasticsearch

from app.core.config import settings
from app.models.document import Document


def index_document(document: Document) -> None:
    try:
        client = Elasticsearch(settings.elasticsearch_url)
        client.index(
            index="ppt-hunter-documents",
            id=document.id,
            document={
                "title": document.title,
                "url": document.source_url,
                "file_type": document.file_type,
                "status": document.status,
                "category": document.category,
                "summary": document.summary,
                "text": document.extracted_text,
                "created_at": document.created_at.isoformat(),
            },
        )
    except Exception:
        # Search indexing should not fail the ingestion pipeline.
        return

