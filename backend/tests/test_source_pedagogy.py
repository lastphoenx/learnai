import json

from app.ai.source_pedagogy import (
    build_pedagogy_digest,
    decode_source_analysis,
    encode_source_analysis,
    has_pedagogy_content,
    merge_pedagogy_profiles,
    parse_pedagogy_extraction,
)


def test_parse_pedagogy_extraction_json():
    payload = {
        "summary": "Dezimalzahlen addieren mit verschiedenen Lösungswegen.",
        "is_metadata_only": False,
        "methods": [
            {
                "id": "mental",
                "label": "im Kopf",
                "when": "bei einfachen Zahlen",
                "example": "3,7 + 20,1",
            }
        ],
        "worked_examples": [
            {
                "problem": "24 · 9,36",
                "method_id": "decomposition",
                "steps": ["20 · 9,36", "4 · 9,36", "addieren"],
            }
        ],
        "exercises": [{"ref": "Aufg. 5a", "text": "8 · 2,22"}],
        "exercise_patterns": ["vorgehen_waehlen"],
        "teaching_notes": ["Dezimalpunkte untereinander ausrichten"],
    }
    summary, pedagogy = parse_pedagogy_extraction(json.dumps(payload))
    assert "Dezimalzahlen" in summary
    assert pedagogy["methods"][0]["label"] == "im Kopf"
    assert pedagogy["worked_examples"][0]["problem"] == "24 · 9,36"


def test_merge_pedagogy_profiles_dedupes_methods():
    a = {
        "is_metadata_only": False,
        "methods": [{"id": "mental", "label": "im Kopf", "when": "einfach", "example": ""}],
        "worked_examples": [],
        "exercises": [],
        "exercise_patterns": [],
        "teaching_notes": [],
    }
    b = {
        "is_metadata_only": False,
        "methods": [{"id": "mental", "label": "im Kopf", "when": "einfach", "example": ""}],
        "worked_examples": [{"problem": "1 + 2", "steps": ["3"]}],
        "exercises": [],
        "exercise_patterns": ["zuordnen"],
        "teaching_notes": [],
    }
    merged = merge_pedagogy_profiles([a, b])
    assert len(merged["methods"]) == 1
    assert len(merged["worked_examples"]) == 1
    assert merged["exercise_patterns"] == ["zuordnen"]


def test_build_pedagogy_digest_includes_methods_and_verstehen_examples():
    profile = {
        "is_metadata_only": False,
        "methods": [{"id": "written", "label": "schriftlich", "when": "grosse Zahlen", "example": ""}],
        "worked_examples": [{"problem": "0,726 + 8,607", "steps": ["+0,007", "+0,6", "+8"]}],
        "exercises": [],
        "exercise_patterns": ["vorgehen_waehlen"],
        "teaching_notes": ["Zuerst Vorgehen wählen"],
    }
    digest = build_pedagogy_digest(profile)
    assert "schriftlich" in digest
    assert "Verstehen" in digest
    assert "Vorgehen wählen" in digest


def test_encode_decode_source_analysis_roundtrip():
    pedagogy = {"methods": [{"id": "mental", "label": "im Kopf", "when": "", "example": ""}]}
    raw = encode_source_analysis(provider="openai", model="gpt-4o", pedagogy=pedagogy)
    parsed = decode_source_analysis(raw)
    assert parsed is not None
    assert parsed["provider"] == "openai"
    assert parsed["pedagogy"]["methods"][0]["label"] == "im Kopf"


def test_has_pedagogy_content_and_digest_do_not_crash():
    assert has_pedagogy_content({}) is False
    assert has_pedagogy_content({"methods": [{"id": "mental", "label": "im Kopf"}]}) is True
    digest = build_pedagogy_digest({})
    assert "Keine strukturierten Didaktik-Hinweise" in digest


def test_decode_legacy_provider_model_string():
    parsed = decode_source_analysis("openai:gpt-4o")
    assert parsed is not None
    assert parsed["provider"] == "openai"
    assert parsed["pedagogy"] == {}
