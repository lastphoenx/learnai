#!/usr/bin/env python3
"""Einmalig Fixtures für task_type_golden erzeugen (idempotent)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.ai.task_types import UNIT_TASK_TYPES  # noqa: E402
from app.services.task_type_golden_service import validate_task_type_fixture  # noqa: E402

OUT = ROOT / "app" / "fixtures" / "task_type_golden"


def _words(count: int, prefix: str) -> str:
    return " ".join(f"{prefix}{i}" for i in range(1, count + 1))


def _long_text(topic: str, words: int = 130) -> str:
  base = (
      f"Dieser Block erklärt {topic} Schritt für Schritt mit Beispielen aus dem Schulheft. "
      "Wir wiederholen die wichtigsten Begriffe, zeigen einen Rechenweg und verbinden "
      "die Aufgabe mit dem bereits bekannten Stoff. "
  )
  extra = _words(max(0, words - len(base.split())), "inhalt")
  return f"{base}{extra}"


def _questions(
    *,
    count: int,
    prefix: str,
    with_explanation: bool = True,
    explanation: str | None = None,
) -> list[dict]:
    items: list[dict] = []
    for i in range(count):
        q = {
            "q": f"{prefix} Frage {i + 1}?",
            "options": [f"Antwort A{i}", f"Antwort B{i}", f"Antwort C{i}", f"Antwort D{i}"],
            "answer": 0,
        }
        if with_explanation:
            q["explanation"] = explanation or (
                f"Variante 1: 12 + 8 = 20. Variante 2: 10 + 8 = 18, dann +2 = 20."
            )
        items.append(q)
    return items


def _standard_module(title: str, topic: str, *, q_count: int = 4, with_explanation: bool = True) -> dict:
    return {
        "title": title,
        "content": {"text": _long_text(topic)},
        "quiz": {"questions": _questions(count=q_count, prefix=title, with_explanation=with_explanation)},
    }


def _build_standard(task: str, *, module_count: int = 5, q_count: int = 4, with_explanation: bool = True) -> list[dict]:
    label = next(item["label"] for item in UNIT_TASK_TYPES if item["key"] == task)
    return [
        _standard_module(
            f"Block {index + 1}",
            f"{label} — Thema {index + 1}",
            q_count=q_count,
            with_explanation=with_explanation,
        )
        for index in range(module_count)
    ]


def _build_vocab() -> list[dict]:
    modules = []
    for index in range(5):
        modules.append(
            {
                "title": f"Vokabeln Set {index + 1}",
                "content": {
                    "text": (
                        "Wort: apple — Bedeutung: Apfel — Beispiel: I eat an apple every day. "
                        "Wort: house — Bedeutung: Haus — Beispiel: This is my house. "
                        + _long_text("Englisch Vokabeln", 110)
                    ),
                    "practice": [
                        {
                            "prompt": "Übersetze: book",
                            "answer": "Buch",
                            "hint": "Schulbuch",
                            "answer_type": "text",
                        }
                    ],
                },
                "quiz": {
                    "questions": _questions(count=4, prefix="Vokabel", with_explanation=False)
                },
            }
        )
    return modules


def _build_math() -> list[dict]:
    modules = []
    for index in range(5):
        modules.append(
            {
                "title": f"Rechnen {index + 1}",
                "content": {
                    "text": _long_text("Dezimalrechnung", 130),
                    "practice": [
                        {
                            "prompt": "Berechne 3,2 + 4,8",
                            "answer": "8",
                            "hint": "Komma unter Komma",
                            "answer_type": "number",
                        }
                    ],
                },
                "quiz": {
                    "questions": [
                        {
                            "q": f"Was ist 7,2 : 9 in Bereich {index + 1}?",
                            "options": ["0,8", "0,08", "8", "0,72"],
                            "answer": 0,
                            "explanation": (
                                "Variante 1: 72 ÷ 9 = 8, Komma eine Stelle → 0,8. "
                                "Variante 2: 72 ÷ 9 = 8, das sind 8 Zehntel = 0,8."
                            ),
                        },
                        *_questions(count=3, prefix=f"Mathe {index + 1}"),
                    ],
                },
            }
        )
    return modules


def _build_interactive() -> list[dict]:
    modules = []
    for area in range(4):
        modules.append(
            {
                "title": f"Bereich {area + 1}",
                "content": {
                    "cards": [
                        {
                            "question": f"Lernkarte {area + 1}-{card + 1}?",
                            "answer": f"Antwort {area + 1}-{card + 1} mit kurzer Erklärung.",
                        }
                        for card in range(8)
                    ],
                    "knowledge": [{"title": "Merke", "text": "Wichtiger Fakt aus dem Heft."}],
                },
                "quiz": {
                    "questions": [
                        {
                            "q": f"Quiz {area + 1}-{quiz + 1}: Was ist 6 · 7?",
                            "options": ["42", "36", "48", "40"],
                            "answer": 0,
                            "explanation": "Variante 1: 6 · 7 = 42. Variante 2: 6 · 5 = 30, 6 · 2 = 12, 30 + 12 = 42.",
                        },
                        *[
                            {
                                "q": f"Quiz {area + 1}-{quiz + 1}?",
                                "options": ["A", "B", "C", "D"],
                                "answer": 0,
                            }
                            for quiz in range(1, 8)
                        ],
                    ],
                },
            }
        )
    return modules


BUILDERS = {
    "mixed": lambda: _build_standard("mixed"),
    "explain": lambda: _build_standard("explain", q_count=2),
    "quiz": lambda: _build_standard("quiz"),
    "practice": lambda: _build_standard("practice"),
    "math": _build_math,
    "workbook": lambda: _build_standard("workbook"),
    "review": lambda: _build_standard("review"),
    "exam": lambda: _build_standard("exam", with_explanation=False),
    "vocab": _build_vocab,
    "interactive": _build_interactive,
}

HINTS = {
    "mixed": "Bruchrechnen Klasse 5",
    "explain": "Photosynthese Einstieg",
    "quiz": "Erdkunde Europa",
    "practice": "Satzglieder üben",
    "math": "Dezimalrechnung",
    "workbook": "Arbeitsblatt Addition",
    "review": "Wiederholung Multiplikation",
    "exam": "Kurzprüfung Grammatik",
    "vocab": "Englisch Tiere",
    "interactive": "Trainer Dezimalzahlen",
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for task in BUILDERS:
        modules = BUILDERS[task]()
        meta = {
            "task_type": task,
            "subject_hint": HINTS[task],
        }
        if task == "interactive":
            meta["min_cards"] = 30
            meta["min_questions"] = 30
        payload = {"_meta": meta, "modules": modules}
        validate_task_type_fixture(
            {"modules": modules},
            task_type=task,
            fixture_name=task,
            min_cards=int(meta.get("min_cards") or 8),
            min_questions=int(meta.get("min_questions") or 8),
        )
        path = OUT / f"{task}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {path.name}")


if __name__ == "__main__":
    main()
