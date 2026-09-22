"""Redis-Job-Heartbeat während blockierender LLM-Calls (Stale-Wächter)."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")

_DEFAULT_INTERVAL_SEC = 90


def run_with_generate_heartbeat(
    progress: Callable[..., None] | None,
    *,
    stage: str = "running",
    message: str = "KI-Anfrage läuft…",
    interval_sec: int = _DEFAULT_INTERVAL_SEC,
    fn: Callable[[], T],
    **progress_extra: Any,
) -> T:
    """Hält `updated_at` am Leben, solange `fn()` blockiert (z. B. Cloud-Vision)."""
    if progress is None or interval_sec <= 0:
        return fn()

    stop = threading.Event()

    def _tick() -> None:
        while not stop.wait(interval_sec):
            try:
                progress(stage, message=message, **progress_extra)
            except Exception:
                break

    thread = threading.Thread(target=_tick, name="generate-heartbeat", daemon=True)
    thread.start()
    try:
        return fn()
    finally:
        stop.set()
        thread.join(timeout=1.0)
