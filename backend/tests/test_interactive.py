from app.ai.validators.interactive import dedupe_interactive_modules, validate_interactive_modules


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
