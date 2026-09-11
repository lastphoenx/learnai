from app.ai.validators.interactive import (
    dedupe_interactive_modules,
    sanitize_interactive_modules,
    trim_interactive_modules_to_budget,
    validate_interactive_modules,
)


def test_validate_interactive_counts():
    modules = []
    for i in range(4):
        modules.append(
            {
                "title": f"Bereich {i}",
                "content": {
                    "cards": [
                        {"question": f"Frage {i}-{j}?", "answer": f"Antwort {i}-{j}."}
                        for j in range(8)
                    ],
                    "knowledge": [{"title": "T", "text": "Wissen"}],
                },
                "quiz": {
                    "questions": [
                        {
                            "q": f"Quiz {i}-{j}?",
                            "options": ["A", "B", "C", "D"],
                            "answer": 0,
                        }
                        for j in range(8)
                    ]
                },
            }
        )
    validate_interactive_modules(modules, min_cards=30, min_questions=30)


def test_dedupe_removes_duplicate_quiz_and_passes_validation():
    modules = []
    for i in range(4):
        modules.append(
            {
                "title": f"Bereich {i}",
                "content": {
                    "cards": [
                        {"question": f"Frage {i}-{j}?", "answer": f"Antwort {i}-{j}."}
                        for j in range(8)
                    ],
                    "knowledge": [{"title": "T", "text": "Wissen"}],
                },
                "quiz": {
                    "questions": [
                        {
                            "q": f"Quiz {i}-{j}?",
                            "options": ["A", "B", "C", "D"],
                            "answer": 0,
                        }
                        for j in range(8)
                    ]
                },
            }
        )
    # Gleiche Frage wie in Bereich 0 — würde validate ohne dedupe abbrechen
    modules[3]["quiz"]["questions"][0]["q"] = "Quiz 0-0?"

    modules, warnings = dedupe_interactive_modules(modules)
    assert len(warnings) == 1
    assert "Duplikat Quizfrage" in warnings[0]
    validate_interactive_modules(modules, min_cards=30, min_questions=30)


def test_trim_interactive_modules_to_budget():
    modules = []
    for i in range(5):
        modules.append(
            {
                "title": f"Bereich {i}",
                "content": {
                    "cards": [
                        {"question": f"Frage {i}-{j}?", "answer": f"A {i}-{j}."}
                        for j in range(14)
                    ],
                },
                "quiz": {
                    "questions": [
                        {
                            "q": f"Quiz {i}-{j}?",
                            "options": ["A", "B", "C", "D"],
                            "answer": 0,
                        }
                        for j in range(3)
                    ]
                },
            }
        )
    trimmed = trim_interactive_modules_to_budget(modules, max_cards=12, max_questions=8)
    total_cards = sum(len(m["content"]["cards"]) for m in trimmed)
    total_quiz = sum(len(m["quiz"]["questions"]) for m in trimmed)
    assert total_cards <= 12
    assert total_quiz <= 8


def test_trim_interactive_modules_keeps_min_cards_per_module():
    modules = []
    for i in range(5):
        modules.append(
            {
                "title": f"Bereich {i}",
                "content": {
                    "cards": [
                        {"question": f"Frage {i}-{j}?", "answer": f"A {i}-{j}."}
                        for j in range(6)
                    ],
                },
                "quiz": {"questions": []},
            }
        )
    trimmed = trim_interactive_modules_to_budget(
        modules, max_cards=12, min_cards_per_module=1
    )
    for raw in trimmed:
        content = raw.get("content") if isinstance(raw.get("content"), dict) else {}
        assert len(content.get("cards") or []) >= 1
    total = sum(len(m["content"]["cards"]) for m in trimmed)
    assert total <= 12


def test_sanitize_interactive_modules_removes_weak_mental_cards():
    modules = [
        {
            "title": "Römerzeit",
            "content": {
                "cards": [
                    {
                        "kind": "mental",
                        "question": "Was bedeutet «Vindonissa» bei Vindonissa?",
                        "answer": "Vindonissa: Von Vindonissa aus kontrollierten die Römer die Umgebung.",
                    },
                    {
                        "kind": "mental",
                        "question": "Was bedeutet «Schwertgriff aus Knochen» bei Waffen und Helmteile?",
                        "answer": "Schwertgriff aus Knochen: Schwertgriff",
                    },
                    {
                        "kind": "input",
                        "question": "Vindonissa war ein römisches ___.",
                        "answer": "Legionslager",
                    },
                ]
            },
            "quiz": {"questions": []},
        }
    ]
    cleaned, warnings = sanitize_interactive_modules(modules)
    cards = cleaned[0]["content"]["cards"]
    assert len(cards) == 1
    assert cards[0]["kind"] == "input"
    assert len(warnings) == 2


def test_parse_plan_compact_accepts_three_categories():
    from app.ai.generate_interactive import _coalesce_plan_categories, _parse_plan

    text = """{"categories":[
        {"name":"A","focus":"f1"},
        {"name":"B","focus":"f2"},
        {"name":"C","focus":"f3"}
    ]}"""
    categories = _parse_plan(text, compact=True)
    assert len(categories) == 3
    assert categories[0]["name"] == "A"


def test_coalesce_plan_categories_merges_overflow():
    from app.ai.generate_interactive import _coalesce_plan_categories

    raw = [{"name": f"Bereich {i}", "focus": f"Fokus {i}"} for i in range(6)]
    merged = _coalesce_plan_categories(raw, max_categories=3)
    assert len(merged) == 3
    assert merged[-1]["name"] == "Bereich 3"
    assert "Fokus 5" in merged[-1]["focus"]


def test_plan_system_compact_mentions_three_categories():
    from app.ai.prompts.interactive import plan_system_for_preset

    compact = plan_system_for_preset(compact=True)
    standard = plan_system_for_preset(compact=False)
    assert "2 bis 3" in compact
    assert "5 bis 6" in standard
