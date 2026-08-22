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
                "label": "im Kopf",
                "when": "bei einfachen Zahlen",
                "example": "3,7 + 20,1",
            },
            {
                "label": "Faktorisierung nach Ausklammern",
                "when": "bei gemeinsamen Faktoren",
            },
        ],
        "worked_examples": [
            {
                "problem": "24 · 9,36",
                "method_label": "Zerlegung",
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
    assert pedagogy["methods"][0].get("id") == "mental"
    assert pedagogy["methods"][1]["label"] == "Faktorisierung nach Ausklammern"
    assert "id" not in pedagogy["methods"][1]
    assert pedagogy["worked_examples"][0]["problem"] == "24 · 9,36"
    assert pedagogy["worked_examples"][0]["method_label"] == "Zerlegung"


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
    assert "vorgehen waehlen" in digest


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


def test_parse_pedagogy_strips_schema_placeholder_echoes():
    payload = {
        "summary": "Dezimalzahlen mit verschiedenen Lösungswegen.",
        "is_metadata_only": False,
        "methods": [
            {
                "label": "Ich notiere meine Rechenschritte.",
                "when": "Wann diese Methode sinnvoll ist",
                "example": "kurzes Beispiel aus dem Bild",
            },
            {
                "label": "Im Kopf rechnen",
                "when": "Wenn eine einfache Rechnung im Kopf ausreicht",
                "example": "3,7 + 20,1",
            },
        ],
        "exercise_patterns": [
            "Addieren von Dezimalzahlen",
            "freier Kurzname für erkannten Aufgabentyp",
        ],
        "teaching_notes": ["didaktische Hinweise aus dem Material", "Komma untereinander ausrichten"],
    }
    _, pedagogy = parse_pedagogy_extraction(json.dumps(payload))
    assert pedagogy["methods"][0]["label"] == "Ich notiere meine Rechenschritte."
    assert pedagogy["methods"][0].get("when") == ""
    assert pedagogy["methods"][0].get("example") == ""
    assert pedagogy["methods"][1]["when"] == "Wenn eine einfache Rechnung im Kopf ausreicht"
    assert pedagogy["exercise_patterns"] == ["Addieren von Dezimalzahlen"]
    assert pedagogy["teaching_notes"] == ["Komma untereinander ausrichten"]
    digest = build_pedagogy_digest(pedagogy)
    assert "Wann diese Methode sinnvoll ist" not in digest
    assert "freier Kurzname" not in digest


def test_parse_pedagogy_strips_new_schema_placeholder_echoes():
    payload = {
        "summary": "2-6 Sätze: Thema, Seiteninhalt, Lernziele",
        "is_metadata_only": False,
        "methods": [
            {
                "label": "Ich notiere meine Rechenschritte.",
                "when": "kurzer Satz: wann passt diese Strategie (aus dem Material)",
                "example": "kurzes Beispiel mit Zahlen/Text aus dem Bild",
            },
            {
                "label": "Im Kopf rechnen",
                "when": "Wenn Zahlen einfach im Kopf lösbar sind",
                "example": "3,7 + 20,1",
            },
        ],
        "exercise_patterns": ["kurzer Name des Aufgabentyps aus dem Heft", "Dezimalzahlen addieren"],
        "teaching_notes": ["konkreter didaktischer Hinweis aus dem Material"],
    }
    summary, pedagogy = parse_pedagogy_extraction(json.dumps(payload))
    assert summary == ""
    assert pedagogy["methods"][0].get("when") == ""
    assert pedagogy["methods"][0].get("example") == ""
    assert pedagogy["methods"][1]["when"] == "Wenn Zahlen einfach im Kopf lösbar sind"
    assert pedagogy["exercise_patterns"] == ["Dezimalzahlen addieren"]
    assert pedagogy["teaching_notes"] == []
    digest = build_pedagogy_digest(pedagogy)
    assert "kurzer Satz" not in digest
    assert "kurzes Beispiel mit Zahlen" not in digest


def test_vision_pedagogy_prompt_uses_empty_schema_values():
    from app.ai.source_pedagogy import vision_pedagogy_prompt

    prompt = vision_pedagogy_prompt(language="de")
    assert '"label":""' in prompt
    assert "kurzer Satz: wann passt diese Strategie" not in prompt
    assert "kurzes Beispiel mit Zahlen/Text aus dem Bild" not in prompt
    assert "Bezeichnung exakt wie im Heft" not in prompt.split("Feldbedeutung:")[0]


def test_parse_pedagogy_strips_placeholder_method_label_from_worked_examples():
    payload = {
        "summary": "Dezimalzahlen.",
        "is_metadata_only": False,
        "methods": [],
        "worked_examples": [
            {
                "problem": "Aufgabe 4a",
                "method_label": "Bezeichnung wie im Heft",
                "steps": ["0,941 + 0,209 = 1,150"],
            }
        ],
    }
    _, pedagogy = parse_pedagogy_extraction(json.dumps(payload))
    example = pedagogy["worked_examples"][0]
    assert "method_label" not in example
    digest = build_pedagogy_digest(
        {
            "is_metadata_only": False,
            "methods": [],
            "worked_examples": [example],
            "exercises": [],
            "exercise_patterns": [],
            "teaching_notes": [],
        }
    )
    assert "Bezeichnung wie im Heft" not in digest
    assert "Aufgabe 4a" in digest
