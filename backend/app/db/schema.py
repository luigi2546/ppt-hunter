from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def ensure_schema(engine: Engine) -> None:
    inspector = inspect(engine)
    if not inspector.has_table("documents"):
        return

    document_columns = {column["name"] for column in inspector.get_columns("documents")}
    if "storage_key" not in document_columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE documents ADD COLUMN storage_key TEXT"))
    if "image_count" not in document_columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE documents ADD COLUMN image_count INTEGER"))
