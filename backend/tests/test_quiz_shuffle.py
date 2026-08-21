import random

from app.ai.quiz_shuffle import shuffle_quiz_block, shuffle_quiz_question


def test_shuffle_moves_correct_option_with_answer_index():
    q = {
        "q": "Was ist 0.5 + 0.25?",
        "options": ["0.75", "0.5", "1.0", "0.25"],
        "answer": 0,
        "explanation": "0.5 + 0.25 = 0.75",
    }
    random.seed(42)
    shuffled = shuffle_quiz_question(q)
    assert shuffled["options"][shuffled["answer"]] == "0.75"
    assert set(shuffled["options"]) == set(q["options"])


def test_shuffle_spreads_answers_across_positions():
    q = {
        "q": "Test?",
        "options": ["A", "B", "C", "D"],
        "answer": 0,
    }
    positions: set[int] = set()
    for seed in range(200):
        random.seed(seed)
        positions.add(shuffle_quiz_question(q)["answer"])
    assert len(positions) >= 3


def test_shuffle_quiz_block_preserves_count():
    quiz = {
        "questions": [
            {"q": "1?", "options": ["a", "b", "c", "d"], "answer": 0},
            {"q": "2?", "options": ["w", "x", "y", "z"], "answer": 2},
        ]
    }
    random.seed(1)
    out = shuffle_quiz_block(quiz)
    assert len(out["questions"]) == 2
    assert out["questions"][1]["options"][out["questions"][1]["answer"]] == "y"
