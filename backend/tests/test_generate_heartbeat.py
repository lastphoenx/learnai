"""Heartbeat während blockierender Generierung."""

import time

from app.services.generate_heartbeat import run_with_generate_heartbeat


def test_run_with_generate_heartbeat_ticks():
    ticks: list[str] = []

    def progress(stage: str, **extra: object) -> None:
        ticks.append(str(extra.get("message") or stage))

    def slow() -> str:
        time.sleep(0.15)
        return "ok"

    out = run_with_generate_heartbeat(
        progress,
        interval_sec=0.05,
        message="ping",
        fn=slow,
    )
    assert out == "ok"
    assert len(ticks) >= 1
