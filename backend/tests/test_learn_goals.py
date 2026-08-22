from app.core.learn_goals import (
    build_goals_progress,
    merge_goals_payload,
    motivational_message,
    normalize_learn_goals,
    resolve_target,
)


def test_normalize_learn_goals():
    goals = normalize_learn_goals(
        {
            "quiz": 20,
            "cards": {"merk": 7, "mental": "all", "input": 4},
            "deadline": "2026-12-31",
        }
    )
    assert goals["quiz"] == 20
    assert goals["cards"]["merk"] == 7
    assert goals["cards"]["mental"] == "all"
    assert goals["deadline"] == "2026-12-31"


def test_resolve_target_all():
    assert resolve_target("all", available=12) == 12
    assert resolve_target(5, available=12) == 5


def test_build_goals_progress_with_bonus():
    progress = build_goals_progress(
        {"quiz": 10, "cards": {"merk": 3}},
        quiz_done=12,
        card_done={"merk": 4, "mental": 0, "input": 0},
        card_available={"merk": 10, "mental": 5, "input": 2},
    )
    quiz_item = next(i for i in progress["items"] if i["key"] == "quiz")
    assert quiz_item["met"] is True
    assert quiz_item["bonus"] == 2
    merk_item = next(i for i in progress["items"] if i["key"] == "merk")
    assert merk_item["bonus"] == 1


def test_motivational_message_almost_done():
    msg = motivational_message(label="quiz", done=8, target=10, bonus=0)
    assert "Fast geschafft" in msg


def test_merge_parent_and_child_goals():
    merged = merge_goals_payload(
        parent_goals={"quiz": 20},
        child_goals={"cards": {"mental": 5}},
        quiz_done=5,
        card_done={"merk": 0, "mental": 2, "input": 0},
        card_available={"merk": 10, "mental": 15, "input": 5},
    )
    assert merged["parent"]["items"][0]["target"] == 20
    assert merged["child"]["items"][0]["key"] == "mental"
