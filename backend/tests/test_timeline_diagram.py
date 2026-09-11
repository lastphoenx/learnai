"""Tests für Zeitstrahl-Erkennung aus key_terms."""

from tests.fixtures.timeline_epochs import POSTEN_14_EPOCH_TERMS
from app.core.timeline_diagram import (
    build_timeline_diagram_from_pedagogy,
    detect_timeline_epochs,
    parse_epoch_year_range,
    summarize_timeline,
)

    assert parse_epoch_year_range("450 bis 1050") == (450, 1050)
    assert parse_epoch_year_range("9500 bis 5500 v. Chr.") == (-9500, -5500)
    assert parse_epoch_year_range("Anfänge der Menschheit bis 9500 v. Chr.")[1] == -9500
    century = parse_epoch_year_range("2. Jahrhundert v. Chr. bis 6. Jahrhundert n. Chr.")
    assert century is not None
    assert century[0] < 0
    assert century[1] > 0
    present = parse_epoch_year_range("1914 bis zur Gegenwart")
    assert present is not None
    assert present[0] == 1914


def test_detect_timeline_epochs_sorts_chronologically():
    epochs = detect_timeline_epochs(POSTEN_14_EPOCH_TERMS)
    assert len(epochs) >= 8
    assert epochs[0]["term"] == "Altsteinzeit"
    assert epochs[-1]["term"].startswith("Neueste")


def test_build_timeline_diagram_from_pedagogy():
    pedagogy = {
        "key_terms": POSTEN_14_EPOCH_TERMS,
        "exercise_patterns": ["Zeitstrahl-Beschreibung"],
        "assignments": [],
    }
    diagram = build_timeline_diagram_from_pedagogy(pedagogy, title="Geschichte — Zeitstrahl")
    assert diagram is not None
    assert diagram["layout"] == "timeline"
    assert len(diagram["hotspots"]) >= 8
    xs = [hs["x"] for hs in diagram["hotspots"]]
    assert xs == sorted(xs)


def test_summarize_timeline():
    summary = summarize_timeline({"key_terms": POSTEN_14_EPOCH_TERMS})
    assert summary is not None
    assert summary["epochs"] >= 8
