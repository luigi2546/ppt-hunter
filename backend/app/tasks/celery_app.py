from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "ppt_hunter",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.jobs"],
)
celery_app.conf.update(
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_always_eager=settings.celery_task_always_eager,
    task_eager_propagates=False,
)
