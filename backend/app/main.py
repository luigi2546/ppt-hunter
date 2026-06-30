from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings
from app.db.schema import ensure_schema
from app.db.session import Base, engine


def create_app() -> FastAPI:
    app = FastAPI(title="PPT Hunter API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def startup() -> None:
        Base.metadata.create_all(bind=engine)
        ensure_schema(engine)

    app.include_router(router, prefix="/api")
    return app


app = create_app()
