from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class SearchRunCreate(BaseModel):
    query: str = Field(min_length=2, max_length=500)
    provider: str = "auto"
    limit: int = Field(default=500, ge=1, le=500)
    auto_download: bool = True


class SearchRunRead(BaseModel):
    id: str
    query: str
    provider: str
    status: str
    result_count: int
    error: str | None
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class DocumentRead(BaseModel):
    id: str
    title: str
    source_url: str
    provider: str
    file_type: str
    status: str
    description: str | None
    sha256: str | None
    size_bytes: int | None
    slide_count: int | None
    language: str | None
    category: str | None
    confidence: float | None
    summary: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentDetail(DocumentRead):
    extracted_text: str | None
    error: str | None


class DocumentStatsRead(BaseModel):
    total: int
    downloaded: int
    ready: int
    completed: int
    left: int
    queued: int
    downloading: int
    failed: int
    by_status: dict[str, int]


class ManualDocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    url: HttpUrl


class ManualLinksCreate(BaseModel):
    urls: list[str] = Field(default_factory=list, max_length=500)


class ManualLinksRead(BaseModel):
    created: int
    existing: int
    queued: int
    skipped: int
    invalid: list[str]
    discovery_runs: int = 0


class BulkDownloadCreate(BaseModel):
    provider: str | None = None
    limit: int = Field(default=500, ge=1, le=500)


class BulkDownloadRead(BaseModel):
    queued: int
    skipped: int


class MetadataExportRead(BaseModel):
    document_count: int
    csv_key: str
    json_key: str


class PublicPortalExportRead(BaseModel):
    document_count: int
    index_key: str
    manifest_key: str
    csv_key: str
    json_key: str
