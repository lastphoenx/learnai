from app.ai.validators.interactive import validate_interactive_modules


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
