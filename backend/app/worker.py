"""Celery-Worker für später KI-Jobs (Kursgenerierung, OCR, TTS)."""

import os

from celery import Celery

celery_app = Celery(
    "learnai",
    broker=os.environ.get("REDIS_URL", "redis://redis:6379/0"),
    backend=os.environ.get("REDIS_URL", "redis://redis:6379/0"),
    include=["app.tasks.generate"],
)


@celery_app.task(name="learnai.ping")
def ping() -> str:
    return "ok"
