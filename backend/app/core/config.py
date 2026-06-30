from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    api_cors_origins: str = "http://localhost:3000"
    database_url: str = "sqlite:///./ppt_hunter.db"
    redis_url: str = "redis://localhost:6379/0"
    elasticsearch_url: str = "http://localhost:9200"
    celery_task_always_eager: bool = False
    storage_dir: Path = Path("./storage")
    storage_backend: str = "local"
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None
    supabase_storage_bucket: str = "ppt-hunter"
    aws_s3_bucket: str | None = None
    aws_region: str = "eu-north-1"
    aws_s3_endpoint_url: str | None = None
    public_archive_title: str = "Research Document Archive"
    public_archive_base_url: str | None = None
    public_archive_target_files: int = 200000
    archive_collection_batch_size: int = 500
    archive_collection_target_files: int = 200000
    archive_collection_wait_seconds: int = 60
    archive_collection_max_empty_batches: int = 5
    archive_collection_stale_download_minutes: int = 30
    min_pptx_image_count: int = 5

    brave_search_api_key: str | None = None
    dataforseo_login: str | None = None
    dataforseo_password: str | None = None
    tika_server_url: str | None = None

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.api_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    (settings.storage_dir / "raw").mkdir(parents=True, exist_ok=True)
    return settings


settings = get_settings()
