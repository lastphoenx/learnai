"""Prompt-Bausteine für KI-Generierung."""

from app.ai.prompts.interactive import (
    build_interactive_card_prompt,
    build_interactive_plan_prompt,
    build_interactive_quiz_prompt,
    learner_style_hint,
)

__all__ = [
    "build_interactive_card_prompt",
    "build_interactive_plan_prompt",
    "build_interactive_quiz_prompt",
    "learner_style_hint",
]
