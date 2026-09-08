"""Deutsch-Grammatik: ein LLM-Call, HTML-ähnliche Struktur, ~54 Aufgaben."""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from collections.abc import Callable

from sqlalchemy.orm import Session

from app.ai.errors import LlmError
from app.ai.generate import _collect_source_notes, _save_generated_modules
from app.ai.generate_interactive import _complete_with_retry, _parse_questions
from app.ai.prompts.german_compact import (
    COMPACT_COUNTS,
    GERMAN_COMPACT_SYSTEM,
    build_german_compact_prompt,
)
from app.ai.providers import parse_json_object
from app.ai.validators.interactive import dedupe_interactive_modules, validate_interactive_modules
from app.core.basiswissen import empty_basiswissen
from app.core.crypto import decrypt_text_master
from app.core.german_case_analysis import (
    build_case_check_spec,
    case_from_label,
    case_label_de,
    extract_case_drill_sentence,
    find_span_for_expected_case,
    format_case_card_question,
    format_case_quiz_question,
    get_case_check_spec,
    repair_case_check,
)
from app.core.grammar_verify import finalize_german_cards_with_drops
from app.core.quiz_numeric import repair_quiz_block
from app.models import LearningRecord, User
from app.services.crypto_json import decrypt_json
from app.services.unit_service import _get_unit_or_404, get_trainer_options

_log = logging.getLogger(__name__)

_COMPACT_NUM_PREDICT = 16384
_MIN_CARDS = 28
_MIN_QUESTIONS = 18
_GENERIC_ANSWER_MIN_LEN = 24


def _parse_knowledge(raw: object) -> list[dict]:
    if not isinstance(raw, list):
        return []
    out: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        text = str(item.get("text") or "").strip()
        if title and text:
            out.append({"title": title[:120], "text": text[:1200]})
    return out[:8]


def _case_answer_label(raw: object) -> str:
    case = case_from_label(str(raw or ""))
    if not case:
        raise ValueError("empty case")
    return case_label_de(case)


def _understand_to_card(raw: dict) -> dict | None:
    sentence = str(raw.get("sentence") or "").strip()
    span = str(raw.get("span") or "").strip()
    if not sentence or not span or span not in sentence:
        return None
    try:
        answer = _case_answer_label(raw.get("answer"))
    except ValueError:
        return None
    explanation = str(raw.get("explanation") or raw.get("why") or "").strip()
    grammar: dict = {"case_check": {"sentence": sentence[:240], "span": span[:120]}}
    nested = raw.get("nested")
    if isinstance(nested, dict):
        nested_span = str(nested.get("span") or nested.get("text") or "").strip()
        try:
            nested_answer = _case_answer_label(nested.get("answer"))
        except ValueError:
            nested_answer = ""
        if nested_span and nested_answer:
            grammar["case_check"]["nested"] = {
                "span": nested_span[:120],
                "answer": nested_answer,
                "explanation": str(nested.get("explanation") or nested.get("why") or "")[:400],
            }
    card = {
        "kind": "input",
        "question": f"Bestimme den Fall der markierten Wortgruppe: «{sentence}»",
        "answer": answer,
        "answer_type": "short_text",
        "tip": explanation[:240],
        "grammar": grammar,
    }
    card = repair_case_check(card, answer=answer)
    return format_case_card_question(card)


def _enrich_case_drill_card(card: dict, *, raw: dict | None = None) -> dict:
    """Fall-Kurzabfragen: span + <mark> wenn eindeutig; sonst Original behalten."""
    answer = str(card.get("answer") or "").strip()
    primary = answer.split("|")[0].strip()
    if not case_from_label(primary):
        return card
    sentence = str((raw or {}).get("sentence") or "").strip()
    span = str((raw or {}).get("span") or "").strip()
    if not sentence:
        sentence = extract_case_drill_sentence(str(card.get("question") or "")) or ""
    if not sentence:
        return card
    spec = build_case_check_spec(sentence=sentence, span=span, expected_answer=primary)
    if not spec:
        return card
    enriched = dict(card)
    grammar: dict = {"case_check": dict(spec)}
    nested = (raw or {}).get("nested")
    if isinstance(nested, dict):
        nested_span = str(nested.get("span") or nested.get("text") or "").strip()
        try:
            nested_answer = _case_answer_label(nested.get("answer"))
        except ValueError:
            nested_answer = ""
        if nested_span and nested_answer:
            grammar["case_check"]["nested"] = {
                "span": nested_span[:120],
                "answer": nested_answer,
                "explanation": str(nested.get("explanation") or nested.get("why") or "")[:400],
            }
    enriched["grammar"] = grammar
    enriched = repair_case_check(enriched, answer=primary)
    if not get_case_check_spec(enriched):
        return card
    enriched = format_case_card_question(enriched)
    if "<mark>" not in str(enriched.get("question") or ""):
        spec2 = get_case_check_spec(enriched) or spec
        marked = spec2["sentence"].replace(
            spec2["span"],
            f"<mark>{spec2['span']}</mark>",
            1,
        )
        enriched["question"] = f"Bestimme den Fall der markierten Wortgruppe: {marked}"[:500]
    return enriched


def _finalize_drill_case_cards(cards: list[dict], *, difficulty: int) -> list[dict]:
    out: list[dict] = []
    dropped = 0
    for card in cards:
        if not get_case_check_spec(card):
            out.append(card)
            continue
        kept, drop_reasons = finalize_german_cards_with_drops(
            [card],
            focus_group="german",
            difficulty=difficulty,
            allow_nested=True,
        )
        if kept:
            out.append(kept[0])
        else:
            dropped += 1
            if drop_reasons:
                _log.warning("german_compact drill_drop %s", drop_reasons[0][:120])
            out.append(card)
    if dropped:
        _log.warning("german_compact drill_case_drops=%d (kept unmarked originals)", dropped)
    return out


def _parse_cards(raw: object) -> tuple[list[dict], list[dict]]:
    if not isinstance(raw, list):
        return [], []
    merk: list[dict] = []
    mental: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind") or "mental").strip().lower()
        q = str(item.get("question") or "").strip()
        a = str(item.get("answer") or "").strip()
        if not q or not a:
            continue
        entry = {
            "kind": "merk" if kind == "merk" else "mental",
            "question": q[:240],
            "answer": a[:2000],
            "tip": str(item.get("tip") or "")[:240],
        }
        if entry["kind"] == "merk" and re.search(
            r"frage\s+(gehört|probe)|wer\s+oder\s+was|wessen|wem|wen\s+oder\s+was",
            q,
            re.I,
        ):
            entry["card_role"] = "term"
        if entry["kind"] == "mental":
            entry = _enrich_case_drill_card(entry, raw=item)
        if entry["kind"] == "merk":
            merk.append(entry)
        else:
            mental.append(entry)
    return merk[: COMPACT_COUNTS["merk_cards"]], mental[: COMPACT_COUNTS["mental_cards"]]


def _parse_understand(raw: object) -> list[dict]:
    if not isinstance(raw, list):
        return []
    out: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        card = _understand_to_card(item)
        if card:
            out.append(card)
    return out[: COMPACT_COUNTS["understand"]]


def _extract_quiz_sentence(text: str) -> str:
    q = str(text or "").strip()
    for marker in (
        "markierten Wortgruppe:",
        "markierten Wortgruppe",
        "markierten Satzglieds:",
        "markierten Satzglieds",
    ):
        if marker in q:
            tail = q.split(marker, 1)[1].strip().strip("«»\"'")
            return tail[:240]
    if ":" in q:
        tail = q.rsplit(":", 1)[1].strip().strip("«»\"'")
        if len(tail) > 8:
            return tail[:240]
    return ""


def _enrich_compact_quiz(raw_items: list, questions: list[dict]) -> list[dict]:
    enriched: list[dict] = []
    for index, question in enumerate(questions):
        if not isinstance(question, dict):
            continue
        raw = raw_items[index] if index < len(raw_items) and isinstance(raw_items[index], dict) else {}
        sentence = str(raw.get("sentence") or "").strip()
        span = str(raw.get("span") or raw.get("target") or "").strip()
        if not sentence:
            sentence = _extract_quiz_sentence(str(question.get("q") or ""))
        answer_idx = int(question.get("answer") or 0)
        options = question.get("options") if isinstance(question.get("options"), list) else []
        expected = str(options[answer_idx] if 0 <= answer_idx < len(options) else "").strip()
        if not span and sentence and expected:
            span = find_span_for_expected_case(sentence=sentence, expected_answer=expected) or ""
        item = dict(question)
        if sentence and span:
            grammar: dict = {"case_check": {"sentence": sentence[:240], "span": span[:120]}}
            nested = raw.get("nested")
            if isinstance(nested, dict):
                nested_span = str(nested.get("span") or nested.get("text") or "").strip()
                nested_case = case_from_label(str(nested.get("answer") or ""))
                nested_answer = case_label_de(nested_case) if nested_case else ""
                if nested_span and nested_answer and nested_answer != "?":
                    grammar["case_check"]["nested"] = {
                        "span": nested_span[:120],
                        "answer": nested_answer,
                        "explanation": str(nested.get("explanation") or nested.get("why") or "")[:400],
                    }
            item["grammar"] = grammar
            item = repair_case_check(item, answer=expected)
            item = format_case_quiz_question(item)
        enriched.append(item)
    return enriched


def _parse_compact_payload(text: str) -> dict:
    parsed = parse_json_object(text)
    if not isinstance(parsed, dict):
        raise LlmError("Kompakt-Trainer: kein JSON-Objekt", "bad_json")
    theory = parsed.get("theory") if isinstance(parsed.get("theory"), dict) else {}
    understand = _parse_understand(parsed.get("understand"))
    merk, mental = _parse_cards(parsed.get("cards"))
    quiz_raw = parsed.get("quiz")
    quiz_list = quiz_raw if isinstance(quiz_raw, list) else []
    questions = _parse_questions(
        json.dumps({"questions": quiz_list}, ensure_ascii=False),
        COMPACT_COUNTS["quiz"],
    )
    questions = _enrich_compact_quiz(quiz_list, questions)
    min_understand = max(6, int(COMPACT_COUNTS["understand"] * 0.5))
    min_cards = max(12, COMPACT_COUNTS["merk_cards"] + COMPACT_COUNTS["mental_cards"] - 4)
    if len(understand) < min_understand:
        raise LlmError(
            f"Verstehen-Aufgaben unvollständig ({len(understand)}/{COMPACT_COUNTS['understand']})",
            "thin_content",
        )
    if len(merk) + len(mental) < min_cards // 2:
        raise LlmError(
            f"Lernkarten unvollständig ({len(merk) + len(mental)})",
            "thin_content",
        )
    return {
        "theory": theory,
        "understand_cards": understand,
        "merk_cards": merk,
        "mental_cards": mental,
        "quiz_questions": questions,
    }


def _collapse_duplicate_mental_answers(cards: list[dict]) -> list[dict]:
    """Kürzt nur lange, kopierte Erklärtexte — kurze Fall-Labels (Nominativ …) bleiben."""
    kept: list[dict] = []
    answer_counts: dict[str, int] = {}
    for card in cards:
        if not isinstance(card, dict):
            kept.append(card)
            continue
        if str(card.get("kind") or "") != "mental":
            kept.append(card)
            continue
        answer = str(card.get("answer") or "").strip()
        if len(answer) < _GENERIC_ANSWER_MIN_LEN:
            kept.append(card)
            continue
        answer_key = answer.lower()
        count = answer_counts.get(answer_key, 0)
        if count >= 2:
            continue
        answer_counts[answer_key] = count + 1
        kept.append(card)
    return kept


def _finalize_cards(cards: list[dict], *, difficulty: int) -> list[dict]:
    kept, _ = finalize_german_cards_with_drops(
        cards,
        focus_group="german",
        difficulty=difficulty,
    )
    out: list[dict] = []
    for card in kept:
        if card.get("kind") == "input":
            card = repair_case_check(card, answer=str(card.get("answer") or ""))
            card = format_case_card_question(card)
        out.append(card)
    return out


def compact_payload_to_modules(payload: dict, *, title: str, difficulty: int) -> list[dict]:
    theory = payload.get("theory") if isinstance(payload.get("theory"), dict) else {}
    intro = str(theory.get("intro") or "").strip()
    knowledge = _parse_knowledge(theory.get("knowledge"))
    cases = theory.get("cases") if isinstance(theory.get("cases"), list) else []
    for case in cases[:4]:
        if not isinstance(case, dict):
            continue
        name = str(case.get("name") or "").strip()
        question = str(case.get("question") or "").strip()
        example = str(case.get("example") or "").strip()
        if name and question:
            knowledge.append(
                {
                    "title": f"{name} — {question}",
                    "text": example or question,
                }
            )

    understand_cards = _finalize_cards(list(payload.get("understand_cards") or []), difficulty=difficulty)
    drill_cards = _collapse_duplicate_mental_answers(
        list(payload.get("merk_cards") or []) + list(payload.get("mental_cards") or [])
    )
    drill_cards = _finalize_drill_case_cards(drill_cards, difficulty=difficulty)
    quiz_questions = list(payload.get("quiz_questions") or [])
    for q in quiz_questions:
        if isinstance(q, dict):
            q["question_type"] = "concept"

    modules = [
        {
            "title": "Theorie & Einstieg",
            "content": {
                "intro": intro[:600],
                "knowledge": knowledge,
                "cards": [],
                "basiswissen": empty_basiswissen(focus_group="german"),
            },
            "quiz": {"questions": []},
        },
        {
            "title": "Verstehen",
            "content": {
                "intro": "Erkenne den Fall der markierten Wortgruppe — Frageprobe zuerst.",
                "knowledge": [],
                "cards": understand_cards,
                "basiswissen": empty_basiswissen(focus_group="german"),
            },
            "quiz": {"questions": []},
        },
        {
            "title": "Karten üben",
            "content": {
                "intro": "Merke Frageproben, Artikelreihen und typische Formulierungen.",
                "knowledge": [],
                "cards": drill_cards,
                "basiswissen": empty_basiswissen(focus_group="german"),
            },
            "quiz": {"questions": []},
        },
        {
            "title": title[:120] or "Check",
            "content": {
                "intro": "Quiz — Fall erkennen, Artikel, Signalwörter.",
                "knowledge": [],
                "cards": [],
                "basiswissen": empty_basiswissen(focus_group="german"),
            },
            "quiz": {"questions": quiz_questions},
        },
    ]
    return modules


def generate_german_grammar_compact(
    db: Session,
    user: User,
    unit_id: uuid.UUID,
    *,
    provider: str,
    model: str | None,
    title: str,
    brief: str,
    notes: str,
    options: dict,
    progress: Callable[..., None] | None = None,
    provider_override: str | None = None,
) -> dict:
    from app.services.profile_service import resolve_unit_ai_prefs
    from app.services.unit_service import _dec_unit

    unit = _get_unit_or_404(db, user, unit_id)
    target_prefs, fallback_prefs = resolve_unit_ai_prefs(db, user, unit.profile_id)
    difficulty = int(unit.difficulty or 3)
    prompt = build_german_compact_prompt(
        title=title,
        brief=brief,
        subject=unit.subject,
        language=unit.language,
        target_age=unit.target_age,
        difficulty=difficulty,
        style=str(options.get("style") or "playful"),
        answer_length=str(options.get("answer_length") or "short"),
        notes=notes,
    )
    t0 = time.monotonic()
    retry_hint = ""
    result: dict | None = None
    modules: list[dict] = []
    last_exc: LlmError | None = None

    for attempt in (1, 2):
        if progress:
            progress("generating_compact", attempt=attempt)
        result = _complete_with_retry(
            prompt=prompt + retry_hint,
            provider=provider,
            system=GERMAN_COMPACT_SYSTEM,
            model=model,
            num_predict=_COMPACT_NUM_PREDICT,
            label=f"german_compact_{attempt}",
        )
        try:
            payload = _parse_compact_payload(result["text"])
            modules = compact_payload_to_modules(payload, title=title, difficulty=difficulty)
            from app.core.content_qa import collect_content_warnings_for_module, summarize_content_warnings

            qa_warnings: list[dict[str, str]] = []
            for module in modules:
                content = module.get("content") if isinstance(module.get("content"), dict) else {}
                quiz = module.get("quiz") if isinstance(module.get("quiz"), dict) else {}
                qa_warnings.extend(
                    collect_content_warnings_for_module(
                        content=content,
                        quiz=quiz,
                        focus_group="german",
                    )
                )
            qa_summary = summarize_content_warnings(qa_warnings)
            if qa_summary.get("warn"):
                _log.warning(
                    "generate_german_compact content_qa unit_id=%s warn=%d attempt=%d",
                    unit_id,
                    qa_summary["warn"],
                    attempt,
                )
            modules, dedupe_warnings = dedupe_interactive_modules(modules)
            for warning in dedupe_warnings:
                _log.warning("generate_german_compact dedupe unit_id=%s %s", unit_id, warning)
            for module in modules:
                quiz = module.get("quiz") if isinstance(module, dict) else None
                if isinstance(module, dict) and isinstance(quiz, dict):
                    module["quiz"] = repair_quiz_block(quiz)
            validate_interactive_modules(
                modules,
                min_cards=_MIN_CARDS,
                min_questions=_MIN_QUESTIONS,
                min_modules=4,
            )
            last_exc = None
            break
        except LlmError as exc:
            last_exc = exc
            total_try = sum(
                len(m.get("content", {}).get("cards") or [])
                for m in modules
                if isinstance(m, dict)
            )
            _log.warning(
                "generate_german_compact attempt=%d unit_id=%s code=%s msg=%s cards=%d",
                attempt,
                unit_id,
                exc.code,
                exc.message,
                total_try,
            )
            if attempt == 1 and exc.code == "thin_content":
                retry_hint = (
                    "\n\nWICHTIG — vorheriger Versuch zu dünn. "
                    f"Liefere mindestens {COMPACT_COUNTS['understand']} understand, "
                    f"{COMPACT_COUNTS['merk_cards']} merk + {COMPACT_COUNTS['mental_cards']} mental cards "
                    f"und {COMPACT_COUNTS['quiz']} Quizfragen — keine Auslassungen.\n"
                )
                continue
            raise

    if last_exc is not None or result is None:
        assert last_exc is not None
        raise last_exc

    total_cards = sum(len(m["content"]["cards"]) for m in modules)
    total_questions = sum(len(m["quiz"]["questions"]) for m in modules)
    meta = dict(result)
    meta["generation_mode"] = "german_compact"
    if progress:
        progress("saving", cards=total_cards, questions=total_questions)
    _save_generated_modules(
        db,
        unit,
        modules,
        result_meta=meta,
        task="interactive",
        final=True,
    )
    db.commit()
    from app.services.ai_run_snapshot import build_ai_run_snapshot, persist_last_ai_run, resolve_generation_ai_tasks

    persist_last_ai_run(
        db,
        unit_id,
        build_ai_run_snapshot(
            tasks=resolve_generation_ai_tasks(
                target_prefs,
                fallback_prefs,
                "interactive",
                provider_override=provider_override or provider,
                source_count=len(unit.sources or []),
                mixed_result=meta,
            ),
            stats={"modules": len(modules), "cards": total_cards, "questions": total_questions},
            triggered_by=str(user.id),
        ),
    )
    _log.info(
        "generate_german_compact done unit_id=%s cards=%d questions=%d ms=%d",
        unit_id,
        total_cards,
        total_questions,
        int((time.monotonic() - t0) * 1000),
    )
    if progress:
        progress("done", cards=total_cards, questions=total_questions, modules=len(modules))
    return _dec_unit(unit)


def should_use_german_compact(*, focus_group: str, math_focus: str | None) -> bool:
    if focus_group != "german":
        return False
    key = str(math_focus or "").strip().lower()
    return key in {"de_grammar", "lang_grammar"}
