import json

from app.ai.source_pedagogy import (
    PEDAGOGY_ANALYSIS_VERSION,
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


def test_merge_drops_cached_competency_headings_and_wrong_results():
    dirty = {
        "is_metadata_only": False,
        "methods": [
            {
                "label": "Du kannst Additionen und Subtraktionen mit Dezimalzahlen lösen",
                "when": "Themenbuch S.48",
            }
        ],
        "worked_examples": [{"problem": "3,7 + 1,301 = 5,004", "steps": []}],
        "exercises": [],
        "exercise_patterns": [],
        "teaching_notes": ["Die Aufgaben werden mit Kreisen und Strichen korrigiert."],
    }
    clean = {
        "is_metadata_only": False,
        "methods": [{"label": "Kopfrechnen", "when": "einfach", "example": ""}],
        "worked_examples": [],
        "exercises": [],
        "exercise_patterns": [],
        "teaching_notes": [],
    }
    merged = merge_pedagogy_profiles([dirty, clean])
    assert [m["label"] for m in merged["methods"]] == ["Kopfrechnen"]
    assert merged["worked_examples"] == []
    assert merged["teaching_notes"] == []


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
    assert parsed["version"] == PEDAGOGY_ANALYSIS_VERSION
    assert parsed.get("extracted_at")


def test_pedagogy_extract_snapshot_status():
    from app.services.pedagogy_service import pedagogy_extract_snapshot

    ok = pedagogy_extract_snapshot(refreshed=4, skipped_no_file=0)
    assert ok["status"] == "success"
    assert ok["updated_at"]
    partial = pedagogy_extract_snapshot(refreshed=2, skipped_no_file=2)
    assert partial["status"] == "partial"
    failed = pedagogy_extract_snapshot(refreshed=0, skipped_no_file=4)
    assert failed["status"] == "failed"


def test_legacy_analysis_without_version_needs_refresh():
    from app.ai.source_pedagogy import PEDAGOGY_ANALYSIS_VERSION, parsed_analysis_needs_refresh

    stale = {
        "provider": "ollama",
        "model": "qwen2.5:32b",
        "pedagogy": {"methods": [{"label": "im Kopf", "when": "", "example": ""}]},
    }
    assert parsed_analysis_needs_refresh(stale) is True
    current = {
        "provider": "ollama",
        "model": "qwen2.5:32b",
        "version": PEDAGOGY_ANALYSIS_VERSION,
        "pedagogy": {"methods": [{"label": "im Kopf", "when": "", "example": ""}]},
    }
    assert parsed_analysis_needs_refresh(current) is False
    assert parsed_analysis_needs_refresh(None) is True
    empty = {
        "provider": "ollama",
        "model": "x",
        "version": PEDAGOGY_ANALYSIS_VERSION,
        "pedagogy": {"methods": []},
    }
    assert parsed_analysis_needs_refresh(empty) is True


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


def test_parse_pedagogy_empty_summary_when_all_fields_are_placeholders():
    payload = {
        "summary": "2-6 Sätze: Thema, Seiteninhalt, Lernziele",
        "is_metadata_only": False,
        "methods": [
            {
                "label": "Bezeichnung exakt wie im Heft",
                "when": "kurzer Satz: wann passt diese Strategie (aus dem Material)",
                "example": "kurzes Beispiel mit Zahlen/Text aus dem Bild",
            }
        ],
        "worked_examples": [],
        "exercises": [],
        "exercise_patterns": ["kurzer Name des Aufgabentyps aus dem Heft"],
        "teaching_notes": ["konkreter didaktischer Hinweis aus dem Material"],
    }
    raw = json.dumps(payload)
    summary, pedagogy = parse_pedagogy_extraction(raw)
    assert summary == ""
    assert pedagogy["methods"] == []
    assert pedagogy["exercise_patterns"] == []
    assert pedagogy["teaching_notes"] == []
    assert raw not in summary


def test_vision_pedagogy_prompt_uses_empty_schema_values():
    from app.ai.source_pedagogy import vision_pedagogy_prompt

    prompt = vision_pedagogy_prompt(language="de")
    assert '"label":""' in prompt
    assert "kurzer Satz: wann passt diese Strategie" not in prompt
    assert "kurzes Beispiel mit Zahlen/Text aus dem Bild" not in prompt
    assert "Bezeichnung exakt wie im Heft" not in prompt.split("Feldbedeutung:")[0]
    assert "Handschrift" in prompt
    assert "Lernziel-Überschriften" in prompt
    assert "Du kannst" in prompt
    assert "Du kennst" in prompt
    assert "Malpunkt" in prompt
    assert "4 · 60,2" in prompt


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


def test_parse_pedagogy_drops_competency_headings_and_bad_equations():
    payload = {
        "summary": "Dezimalzahlen.",
        "is_metadata_only": False,
        "methods": [
            {
                "label": "Kopfrechnen",
                "when": "bei einfachen Zahlen",
                "example": "0,303 + 0,25",
            },
            {
                "label": "Du kannst Additionen und Subtraktionen mit Dezimalzahlen im Kopf lösen",
                "when": "Themenbuch S.48 Nr.1",
                "example": "",
            },
            {
                "label": "Du kennst ein geeignetes Vorgehen um Multiplikationen zu lösen",
                "when": "Themenbuch S.54",
            },
            {
                "label": "halbschriftlich",
                "when": "bei Multiplikationen mit Dezimalzahlen",
                "example": "4.602 = 240.8",
            },
            {
                "label": "Multiplikationen und Divisionen mit Dezimalzahlen im Kopf, sowie in schriftlicher und halbschriftlicher Form lösen",
                "when": "bei Multiplikationen und Divisionen mit Dezimalzahlen im Kopf, sowie in schriftlicher und halbschriftlicher Form lösen.",
            },
            {
                "label": "Gleichung stimmt",
                "when": "bei Additionen oder Subtraktionen mit Dezimalzahlen so einsetzen, dass die Gleichung stimmt.",
            },
        ],
        "worked_examples": [
            {
                "problem": "3,7 + 1,301 = 5,004",
                "method_label": "Kopfrechnen",
                "steps": ["68,37 + 2,4 = 70,77"],
            },
            {
                "problem": "0,303 + 0,25 = 0,553",
                "method_label": "Kopfrechnen",
                "steps": [
                    "0,300 + 0,250 = 0,550",
                    "2015,37 + 87,075 = 2102,445",
                    "748 - 70,25 = 04,165",
                ],
            },
            {
                "problem": "4.602 = 240.8",
                "steps": ["4 · 60,2"],
            },
            {
                "problem": "3,7 + 1,301 = 5,001",
                "method_label": "Kopfrechnen",
                "steps": ["3,7 + 1,3 = 5,0", "5,0 + 0,001 = 5,001"],
            },
        ],
        "exercises": [
            {"ref": "A1", "text": "Du kannst Additionen und Subtraktionen mit Dezimalzahlen lösen."},
            {"ref": "450:50", "text": "450 : 50"},
        ],
        "exercise_patterns": ["Additionen und Subtraktionen mit Dezimalzahlen"],
        "teaching_notes": [
            "Die Aufgaben sind in verschiedenen Formen zu lösen: Kopfrechnen, schriftlich und halbschriftlich.",
            "Die Aufgaben werden mit Kreisen und Strichen korrigiert.",
        ],
    }
    _, pedagogy = parse_pedagogy_extraction(json.dumps(payload))

    labels = [m["label"] for m in pedagogy["methods"]]
    assert "Kopfrechnen" in labels
    assert "halbschriftlich" in labels
    assert all("Du kannst" not in label and "Du kennst" not in label for label in labels)
    assert not any("Form lösen" in label for label in labels)
    assert "Gleichung stimmt" not in labels
    half = next(m for m in pedagogy["methods"] if m["label"] == "halbschriftlich")
    assert "4.602" not in (half.get("example") or "")

    problems = [ex["problem"] for ex in pedagogy["worked_examples"]]
    assert "3,7 + 1,301 = 5,004" not in problems
    assert "4.602 = 240.8" not in problems
    assert "3,7 + 1,301 = 5,001" in problems
    assert "0,303 + 0,25 = 0,553" in problems

    mashed = next(ex for ex in pedagogy["worked_examples"] if ex["problem"].startswith("0,303"))
    step_blob = " ".join(mashed["steps"])
    assert "04,165" not in step_blob
    assert "2015,37" not in step_blob
    assert "0,300 + 0,250 = 0,550" in mashed["steps"]

    exercise_texts = [ex["text"] for ex in pedagogy["exercises"]]
    assert any("450 : 50" in text for text in exercise_texts)
    assert all("Du kannst" not in text for text in exercise_texts)

    notes = " ".join(pedagogy["teaching_notes"])
    assert "verschiedenen Formen" in notes
    assert "Kreisen" not in notes
    assert "Strichen" not in notes


def test_parse_pedagogy_v3_nmg_fields_and_digest():
    payload = {
        "summary": "Burgen im Hochmittelalter.",
        "is_metadata_only": False,
        "key_terms": [
            {"term": "Bergfried", "definition": "Höchster Turm"},
            {"term": "Wehrgang", "definition": "Gang auf der Mauer"},
        ],
        "assignments": [
            {"ref": "1", "instruction": "Zeichne eine Burg.", "format": "zeichnen"},
        ],
        "exercise_formats": ["Zeichnen/Beschriften"],
        "visual_tasks": [
            {"kind": "zeichnen", "instruction": "Burg zeichnen und beschriften", "terms": ["Bergfried"]},
        ],
        "methods": [],
        "worked_examples": [],
        "exercises": [],
        "exercise_patterns": ["Zeichnen"],
        "teaching_notes": [],
    }
    summary, pedagogy = parse_pedagogy_extraction(json.dumps(payload))
    assert summary
    assert pedagogy["page_summary"]
    assert len(pedagogy["key_terms"]) == 2
    assert pedagogy["assignments"][0]["instruction"].startswith("Zeichne")
    digest = build_pedagogy_digest(pedagogy)
    assert "Fachbegriffe" in digest
    assert "Bergfried" in digest
    assert "Aufträge" in digest
    assert has_pedagogy_content(pedagogy)

