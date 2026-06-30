from pathlib import Path
from urllib.parse import quote

import boto3
import httpx

from app.core.config import settings


CONTENT_TYPES = {
    "ppt": "application/vnd.ms-powerpoint",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}


def storage_backend() -> str:
    return settings.storage_backend.lower().replace("-", "_")


def is_supabase_storage_enabled() -> bool:
    return storage_backend() == "supabase"


def is_s3_storage_enabled() -> bool:
    return storage_backend() in {"s3", "aws_s3"}


def is_remote_storage_enabled() -> bool:
    return is_supabase_storage_enabled() or is_s3_storage_enabled()


def remote_key_for_document(document_id: str, file_type: str) -> str:
    return f"raw/{document_id}.{file_type}"


def upload_downloaded_file(local_path: Path, document_id: str, file_type: str) -> str | None:
    if not is_remote_storage_enabled():
        return None

    key = remote_key_for_document(document_id, file_type)
    upload_file(local_path, key, CONTENT_TYPES.get(file_type, "application/octet-stream"))
    return key


def upload_export_file(local_path: Path) -> str | None:
    if not is_remote_storage_enabled():
        return None

    key = f"exports/{local_path.name}"
    upload_file(local_path, key, "application/zip")
    return key


def ensure_local_file(document_id: str, file_type: str, file_path: str | None, storage_key: str | None) -> Path | None:
    if file_path:
        path = Path(file_path)
        if path.exists():
            return path

    if not storage_key or not is_remote_storage_enabled():
        return None

    target = settings.storage_dir / "raw" / f"{document_id}.{file_type}"
    download_file(storage_key, target)
    return target


def upload_file(local_path: Path, key: str, content_type: str) -> None:
    if is_s3_storage_enabled():
        upload_file_to_s3(local_path, key, content_type)
        return

    bucket = _require_supabase_bucket()
    endpoint = _storage_endpoint(f"object/{bucket}/{quote(key, safe='/')}")
    headers = _auth_headers()
    headers.update({"content-type": content_type, "x-upsert": "true"})

    with local_path.open("rb") as payload:
        response = httpx.post(endpoint, headers=headers, content=payload, timeout=120)
    response.raise_for_status()


def download_file(key: str, target: Path) -> None:
    if is_s3_storage_enabled():
        download_file_from_s3(key, target)
        return

    bucket = _require_supabase_bucket()
    endpoint = _storage_endpoint(f"object/authenticated/{bucket}/{quote(key, safe='/')}")
    target.parent.mkdir(parents=True, exist_ok=True)

    with httpx.stream("GET", endpoint, headers=_auth_headers(), timeout=120) as response:
        response.raise_for_status()
        with target.open("wb") as output:
            for chunk in response.iter_bytes(chunk_size=1024 * 1024):
                output.write(chunk)


def upload_file_to_s3(local_path: Path, key: str, content_type: str) -> None:
    bucket = _require_s3_bucket()
    _s3_client().upload_file(
        str(local_path),
        bucket,
        key,
        ExtraArgs={"ContentType": content_type},
    )


def download_file_from_s3(key: str, target: Path) -> None:
    bucket = _require_s3_bucket()
    target.parent.mkdir(parents=True, exist_ok=True)
    _s3_client().download_file(bucket, key, str(target))


def _storage_endpoint(path: str) -> str:
    if not settings.supabase_url:
        raise ValueError("SUPABASE_URL is required when STORAGE_BACKEND=supabase")
    return f"{settings.supabase_url.rstrip('/')}/storage/v1/{path}"


def _auth_headers() -> dict[str, str]:
    if not settings.supabase_service_role_key:
        raise ValueError("SUPABASE_SERVICE_ROLE_KEY is required when STORAGE_BACKEND=supabase")
    return {
        "authorization": f"Bearer {settings.supabase_service_role_key}",
        "apikey": settings.supabase_service_role_key,
    }


def _require_supabase_bucket() -> str:
    if not settings.supabase_storage_bucket:
        raise ValueError("SUPABASE_STORAGE_BUCKET is required when STORAGE_BACKEND=supabase")
    return settings.supabase_storage_bucket


def _require_s3_bucket() -> str:
    if not settings.aws_s3_bucket:
        raise ValueError("AWS_S3_BUCKET is required when STORAGE_BACKEND=s3")
    return settings.aws_s3_bucket


def _s3_client():
    kwargs = {"region_name": settings.aws_region}
    if settings.aws_s3_endpoint_url:
        kwargs["endpoint_url"] = settings.aws_s3_endpoint_url
    return boto3.client("s3", **kwargs)
