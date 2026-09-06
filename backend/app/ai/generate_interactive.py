"""Interaktiven Lerntrainer erzeugen: Plan → Karten → Quiz pro Kategorie."""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable

from sqlalchemy.orm import Session

from app.ai.catalog import resolve_task_ai
from app.ai.errors import LlmError
from app.ai.generate import _collect_source_notes, _save_generated_modules
from app.core.quiz_numeric import repair_quiz_block
from app.ai.prompts.basiswissen import BASISWISSEN_SYSTEM, build_basiswissen_prompt
from app.ai.prompts.interactive import (
    CARDS_SYSTEM,
    KNOWLEDGE_SYSTEM,
    PLAN_SYSTEM,
    QUIZ_SYSTEM,
    TYPED_CARDS_SYSTEM,
    build_interactive_card_prompt,
    build_interactive_knowledge_prompt,
    build_interactive_plan_prompt,
    build_interactive_quiz_prompt,
    build_interactive_typed_cards_prompt,
    truncate_context,
)
from app.ai.providers import complete, parse_json_object, resolve_provider
from app.ai.source_pedagogy import build_pedagogy_digest, collect_pedagogy_from_unit_sources
from app.ai.task_types import AI_TASK_FOR_UNIT
from app.ai.validators.interactive import (
    dedupe_interactive_modules,
    parse_quiz_answer,
    validate_interactive_modules,
)
from app.core.crypto import decrypt_text_master
from app.core.basiswissen import (
    empty_basiswissen,
    enrich_module_with_basiswissen,
    finalize_basiswissen,
    parse_basiswissen_payload,
    strip_basiswissen_derivatives,
    validate_basiswissen,
)
from app.core.grammar_verify import finalize_german_cards_with_drops
from app.core.answer_match import infer_answer_type
from app.core.method_taxonomy import classify_method, normalize_method_id
from app.core.pedagogy_validation import enforce_label_coverage, log_pedagogy_coverage_warnings
from app.models import LearningRecord, User
from app.services.crypto_json import decrypt_json
from app.services.profile_service import resolve_prefs_for_profile
from app.services.unit_service import _dec_unit, _get_unit_or_404, get_trainer_options
from app.services.user_service import get_user_settings

_log = logging.getLogger(__name__)

_PLAN_NUM_PREDICT = 4096
_BATCH_NUM_PREDICT = 8192
_MIN_CARDS = 30
_MIN_QUESTIONS = 30


def _distribute(total: int, buckets: int) -> list[int]:
    base = total // buckets
    rest = total % buckets
    return [base + (1 if i < rest else 0) for i in range(buckets)]


def _parse_plan(text: str) -> list[dict]:
    parsed = parse_json_object(text)
    categories = parsed.get("categories")
    if not isinstance(categories, list) or len(categories) < 4:
        raise LlmError("Gliederung unvollständig", "thin_content")
    out: list[dict] = []
    for raw in categories[:6]:
        if not isinstance(raw, dict):
            continue
        name = str(raw.get("name") or raw.get("title") or "").strip()
        if not name:
            continue
        out.append(
            {
                "name": name[:120],
                "focus": str(raw.get("focus") or "")[:300],
            }
        )
    if len(out) < 4:
        raise LlmError("Zu wenige Kategorien in der Gliederung", "thin_content")
    return out


def _split_card_kinds(
    total: int,
    *,
    math_focus: str | None = None,
    focus_group: str | None = None,
) -> tuple[int, int, int]:
    if focus_group and focus_group != "math":
        merk_ratio, mental_ratio = 0.35, 0.15
    elif math_focus:
        merk_ratio, mental_ratio = 0.3, 0.3
    else:
        merk_ratio, mental_ratio = 0.45, 0.1
    merk = max(0, round(total * merk_ratio))
    mental = max(0, round(total * mental_ratio))
    input_cards = max(0, total - merk - mental)
    if total > 0 and input_cards == 0:
        input_cards = 1
        if mental > merk:
            mental -= 1
        elif merk > 0:
            merk -= 1
    return merk, mental, input_cards


def _normalize_plan_counts(
    categories: list[dict],
    *,
    card_target: int,
    question_target: int,
    math_focus: str | None = None,
    focus_group: str | None = None,
) -> list[dict]:
    card_parts = _distribute(card_target, len(categories))
    question_parts = _distribute(question_target, len(categories))
    merk_total, mental_total, input_total = _split_card_kinds(
        card_target,
        math_focus=math_focus,
        focus_group=focus_group,
    )
    merk_parts = _distribute(merk_total, len(categories))
    mental_parts = _distribute(mental_total, len(categories))
    input_parts = _distribute(input_total, len(categories))
    normalized: list[dict] = []
    for index, cat in enumerate(categories):
        normalized.append(
            {
                "name": cat["name"],
                "focus": cat.get("focus") or "",
                "cards": card_parts[index],
                "questions": question_parts[index],
                "merk_cards": merk_parts[index],
                "mental_cards": mental_parts[index],
                "input_cards": input_parts[index],
            }
        )
    return normalized


def _parse_cards(text: str, expected: int) -> list[dict]:
    parsed = parse_json_object(text)
    cards = parsed.get("cards")
    if not isinstance(cards, list):
        raise LlmError("Keine Lernkarten in der Antwort", "bad_json")
    out: list[dict] = []
    for raw in cards:
        if not isinstance(raw, dict):
            continue
        q = str(raw.get("question") or "").strip()
        a = str(raw.get("answer") or "").strip()
        if not q or not a:
            continue
        out.append(
            {
                "question": q[:240],
                "answer": a[:2000],
                "tip": str(raw.get("tip") or "")[:240],
            }
        )
    min_accept = max(2, int(expected * 0.6))
    if len(out) < min_accept:
        raise LlmError(f"Lernkarten unvollständig ({len(out)}/{expected})", "thin_content")
    if len(out) < expected:
        _log.warning("generate_interactive cards_short got=%d expected=%d", len(out), expected)
    return out[:expected] if len(out) >= expected else out


def _parse_card_list(raw_cards: object, *, kind: str, expected: int) -> list[dict]:
    if expected <= 0:
        return []
    if not isinstance(raw_cards, list):
        return []
    out: list[dict] = []
    for raw in raw_cards:
        if not isinstance(raw, dict):
            continue
        q = str(raw.get("question") or "").strip()
        a = str(raw.get("answer") or "").strip()
        if not q or not a:
            continue
        item: dict = {
            "kind": kind,
            "question": q[:240],
            "answer": a[:2000],
            "tip": str(raw.get("tip") or "")[:240],
        }
        grammar_raw = raw.get("grammar")
        if isinstance(grammar_raw, dict):
            item["grammar"] = grammar_raw
        if kind == "merk":
            method_label = str(raw.get("method_label") or "").strip()
            if method_label:
                item["method_label"] = method_label[:120]
            method_id = normalize_method_id(raw.get("method_id")) or classify_method(
                f"{method_label} {q} {a}", kind="merk"
            )
            if method_id and method_id != "other":
                item["method_id"] = method_id
        if kind == "input":
            method_label = str(raw.get("method_label") or "").strip()
            if method_label:
                item["method_label"] = method_label[:120]
            answer_type = infer_answer_type(
                question=q,
                answer=a,
                raw_type=str(raw.get("answer_type") or "") or None,
            )
            item["answer_type"] = answer_type
            expected_method = normalize_method_id(raw.get("expected_method")) or classify_method(
                f"{method_label} {q}", kind="input"
            )
            if expected_method and expected_method != "other":
                item["expected_method"] = expected_method
        out.append(item)
    return out[:expected] if len(out) >= expected else out


def _parse_typed_cards(
    text: str,
    *,
    merk_expected: int,
    mental_expected: int,
    input_expected: int,
) -> list[dict]:
    parsed = parse_json_object(text)
    merk = _parse_card_list(parsed.get("merk_cards"), kind="merk", expected=merk_expected)
    mental = _parse_card_list(parsed.get("mental_cards"), kind="mental", expected=mental_expected)
    input_cards = _parse_card_list(parsed.get("input_cards"), kind="input", expected=input_expected)
    total_expected = merk_expected + mental_expected + input_expected
    total_got = len(merk) + len(mental) + len(input_cards)
    min_accept = max(2, int(total_expected * 0.55))
    if total_got < min_accept:
        raise LlmError(f"Lernkarten unvollständig ({total_got}/{total_expected})", "thin_content")
    if len(merk) < merk_expected and merk_expected > 0:
        _log.warning("generate_interactive merk_cards_short got=%d expected=%d", len(merk), merk_expected)
    if len(mental) < mental_expected and mental_expected > 0:
        _log.warning("generate_interactive mental_cards_short got=%d expected=%d", len(mental), mental_expected)
    if len(input_cards) < input_expected and input_expected > 0:
        _log.warning("generate_interactive input_cards_short got=%d expected=%d", len(input_cards), input_expected)
    return merk + mental + input_cards


def _parse_knowledge(text: str, *, fallback_focus: str, category_name: str) -> list[dict]:
    parsed = parse_json_object(text)
    items = parsed.get("knowledge")
    if not isinstance(items, list):
        raise LlmError("Kein Wissens-Hub in der Antwort", "bad_json")
    out: list[dict] = []
    for raw in items:
        if not isinstance(raw, dict):
            continue
        title = str(raw.get("title") or "").strip()
        body = str(raw.get("text") or "").strip()
        if not title or not body:
            continue
        out.append({"title": title[:120], "text": body[:900]})
    if len(out) < 2:
        focus = fallback_focus or f"Kernwissen zu {category_name}."
        return [{"title": "Überblick", "text": focus[:900]}]
    return out[:6]


def _generate_knowledge(
    *,
    batch_context: str,
    cat: dict,
    cards: list[dict],
    provider: str,
    model: str | None,
    index: int,
) -> list[dict]:
    card_summaries = [f"{c['question']} → {c['answer'][:80]}" for c in cards[:8]]
    knowledge_prompt = build_interactive_knowledge_prompt(
        context=batch_context,
        category_name=cat["name"],
        category_focus=cat["focus"],
        card_summaries=card_summaries,
    )
    try:
        knowledge_result = _complete_with_retry(
            prompt=knowledge_prompt,
            provider=provider,
            system=KNOWLEDGE_SYSTEM,
            model=model,
            num_predict=4096,
            label=f"knowledge_{index + 1}",
        )
        return _parse_knowledge(
            knowledge_result["text"],
            fallback_focus=cat.get("focus") or "",
            category_name=cat["name"],
        )
    except LlmError as exc:
        _log.warning(
            "generate_interactive knowledge_fallback category=%s code=%s",
            cat["name"],
            exc.code,
        )
        focus = str(cat.get("focus") or f"Kernwissen zu {cat['name']}.")
        return [{"title": "Überblick", "text": focus[:900]}]


def _generate_basiswissen(
    *,
    batch_context: str,
    cat: dict,
    knowledge: list[dict],
    cards: list[dict],
    provider: str,
    model: str | None,
    index: int,
    focus_group: str,
) -> dict:
    card_summaries = [f"{c['question']} → {c['answer'][:80]}" for c in cards[:8]]
    prompt = build_basiswissen_prompt(
        context=batch_context,
        category_name=cat["name"],
        category_focus=cat.get("focus") or "",
        focus_group=focus_group,
        knowledge_items=knowledge,
        card_summaries=card_summaries,
    )
    try:
        result = _complete_with_retry(
            prompt=prompt,
            provider=provider,
            system=BASISWISSEN_SYSTEM,
            model=model,
            num_predict=4096,
            label=f"basiswissen_{index + 1}",
        )
        parsed = parse_json_object(result["text"])
        basiswissen = parse_basiswissen_payload(parsed, focus_group=focus_group)
        before_cloze = len(basiswissen.get("cloze_templates") or [])
        basiswissen = finalize_basiswissen(basiswissen)
        after_cloze = len(basiswissen.get("cloze_templates") or [])
        if after_cloze < before_cloze:
            _log.warning(
                "generate_interactive basiswissen_cloze_dropped category=%s dropped=%d kept=%d",
                cat["name"],
                before_cloze - after_cloze,
                after_cloze,
            )
        for warning in validate_basiswissen(basiswissen):
            _log.warning(
                "generate_interactive basiswissen_warning category=%s %s",
                cat["name"],
                warning,
            )
        return basiswissen
    except LlmError as exc:
        _log.warning(
            "generate_interactive basiswissen_fallback category=%s code=%s",
            cat["name"],
            exc.code,
        )
        return empty_basiswissen(focus_group=focus_group)


def _parse_questions(text: str, expected: int) -> list[dict]:
    parsed = parse_json_object(text)
    questions = parsed.get("questions")
    if not isinstance(questions, list):
        raise LlmError("Keine Quizfragen in der Antwort", "bad_json")
    out: list[dict] = []
    for raw in questions:
        if not isinstance(raw, dict):
            continue
        options = raw.get("options") if isinstance(raw.get("options"), list) else []
        if len(options) != 4:
            continue
        try:
            item = {
                "q": str(raw.get("q") or "")[:400],
                "options": [str(o)[:200] for o in options[:4]],
                "answer": parse_quiz_answer(raw, label="Quizfrage"),
                "explanation": str(raw.get("explanation") or "")[:1200],
            }
            q_type = str(raw.get("question_type") or "").strip().lower()
            if q_type in {"method", "calculation", "concept"}:
                item["question_type"] = q_type
            elif classify_method(str(raw.get("q") or "")) == "method_choice":
                item["question_type"] = "method"
            else:
                item["question_type"] = "calculation"
            method_id = normalize_method_id(raw.get("method_id"))
            if method_id:
                item["method_id"] = method_id
            elif item.get("question_type") == "method":
                item["method_id"] = "method_choice"
            if not item["q"].strip():
                continue
            if any(not str(o).strip() for o in item["options"]):
                continue
            out.append(item)
        except LlmError:
            continue
    min_accept = max(2, int(expected * 0.6))
    if len(out) < min_accept:
        raise LlmError(f"Quizfragen unvollständig ({len(out)}/{expected})", "thin_content")
    if len(out) < expected:
        _log.warning("generate_interactive questions_short got=%d expected=%d", len(out), expected)
    return out[:expected] if len(out) >= expected else out


def _complete_with_retry(
    *,
    prompt: str,
    provider: str,
    system: str,
    model: str | None,
    num_predict: int,
    label: str,
) -> dict:
    last_exc: LlmError | None = None
    for attempt in (1, 2, 3):
        try:
            result = complete(
                prompt=prompt,
                provider=provider,
                system=system,
                model=model,
                num_predict=num_predict,
                json_mode=True,
            )
            parse_json_object(result["text"])
            return result
        except LlmError as exc:
            last_exc = exc
            _log.warning(
                "generate_interactive %s_fail attempt=%d code=%s msg=%s",
                label,
                attempt,
                exc.code,
                exc.message,
            )
    assert last_exc is not None
    raise last_exc


_GERMAN_CASE_CARDS_RETRY = (
    "\n\nWICHTIG: Fall-Karten nur wenn span im Satz exakt vorkommt und derselbe Fall wie answer ist. "
    "Lieber weniger Fall-Karten als falsche."
)


def _generate_category_cards(
    *,
    batch_context: str,
    cat: dict,
    unit_id: str,
    category_index: int,
    all_card_questions: list[str],
    focus_group: str,
    name: str,
    model: str | None,
) -> list[dict]:
    expected_total = cat["merk_cards"] + cat["mental_cards"] + cat["input_cards"]
    cards: list[dict] = []
    for attempt in (1, 2):
        cards_prompt = build_interactive_typed_cards_prompt(
            context=batch_context,
            category_name=cat["name"],
            category_focus=cat["focus"],
            merk_count=cat["merk_cards"],
            mental_count=cat["mental_cards"],
            input_count=cat["input_cards"],
            existing_questions=all_card_questions,
            focus_group=focus_group,
        )
        if attempt == 2 and focus_group == "german":
            cards_prompt += _GERMAN_CASE_CARDS_RETRY
        cards_result = _complete_with_retry(
            prompt=cards_prompt,
            provider=name,
            system=TYPED_CARDS_SYSTEM,
            model=model,
            num_predict=_BATCH_NUM_PREDICT,
            label=f"cards_{category_index + 1}" + ("_retry" if attempt == 2 else ""),
        )
        cards = _parse_typed_cards(
            cards_result["text"],
            merk_expected=cat["merk_cards"],
            mental_expected=cat["mental_cards"],
            input_expected=cat["input_cards"],
        )
        if not cards:
            cards = _parse_cards(
                cards_result["text"],
                cat["merk_cards"] + cat["mental_cards"] + cat["input_cards"],
            )
            for card in cards:
                card["kind"] = "mental"
        before_case_filter = len(cards)
        cards, dropped_reasons = finalize_german_cards_with_drops(cards, focus_group=focus_group)
        for reason in dropped_reasons[:8]:
            _log.warning(
                "generate_interactive case_card_dropped unit_id=%s category=%s %s",
                unit_id,
                cat["name"],
                reason,
            )
        if len(dropped_reasons):
            _log.warning(
                "generate_interactive case_cards_dropped unit_id=%s category=%s dropped=%d kept=%d",
                unit_id,
                cat["name"],
                before_case_filter - len(cards),
                len(cards),
            )
        min_accept = max(2, int(expected_total * 0.5))
        if attempt == 2 or focus_group != "german" or len(cards) >= min_accept:
            break
        _log.warning(
            "generate_interactive cards_retry unit_id=%s category=%s kept=%d min=%d",
            unit_id,
            cat["name"],
            len(cards),
            min_accept,
        )
    return cards


def generate_interactive_modules(
    db: Session,
    user: User,
    unit_id: uuid.UUID,
    *,
    provider: str | None = None,
    progress: Callable[..., None] | None = None,
) -> dict:
    unit = _get_unit_or_404(db, user, unit_id)
    prefs = resolve_prefs_for_profile(db, unit.profile_id) or get_user_settings(user)
    ai_task = AI_TASK_FOR_UNIT.get("interactive", "mixed")

    record = db.query(LearningRecord).filter(LearningRecord.unit_id == unit.id).first()
    recon = decrypt_json(record.reconstruction_encrypted) if record and record.reconstruction_encrypted else {}
    if not isinstance(recon, dict):
        recon = {}
    options = get_trainer_options(recon)

    effective_provider = provider
    if not effective_provider:
        unit_provider = options.get("llm_provider")
        if isinstance(unit_provider, str) and unit_provider.strip():
            effective_provider = unit_provider.strip()

    name, model = resolve_task_ai(prefs, ai_task, override=effective_provider)
    name = resolve_provider(name)

    title = decrypt_text_master(unit.title_encrypted)
    brief = decrypt_text_master(unit.brief_encrypted) if unit.brief_encrypted else ""

    card_target = int(options["cards"])
    question_target = int(options["questions"])
    style = str(options.get("style") or "playful")
    answer_length = str(options.get("answer_length") or "short")

    _log.info(
        "generate_interactive start unit_id=%s cards=%d questions=%d style=%s sources=%d",
        unit_id,
        card_target,
        question_target,
        style,
        len(unit.sources or []),
    )
    t0 = time.monotonic()
    if progress:
        progress("extracting_sources")
    notes = _collect_source_notes(db, unit, prefs)
    db.commit()
    from app.ai.subject_focus import detect_focus_group

    focus_group = (
        detect_focus_group(subject=unit.subject, task_type=str(unit.task_type or "interactive"))
        or "general"
    )
    pedagogy_profile = collect_pedagogy_from_unit_sources(unit.sources, focus_group=focus_group)
    pedagogy_digest = build_pedagogy_digest(pedagogy_profile)
    _log.info(
        "generate_interactive sources_persisted unit_id=%s notes_chars=%d pedagogy_methods=%d duration_ms=%d",
        unit_id,
        len(notes),
        len(pedagogy_profile.get("methods") or []),
        int((time.monotonic() - t0) * 1000),
    )

    math_focus = (recon or {}).get("math_focus") if isinstance(recon, dict) else None
    math_focus_label: str | None = None
    if math_focus:
        from app.ai.subject_focus import focus_label

        math_focus_label = focus_label(str(math_focus))

    context_prompt = build_interactive_plan_prompt(
        title=title,
        brief=brief,
        subject=unit.subject,
        math_focus=math_focus_label,
        language=unit.language,
        target_age=unit.target_age,
        difficulty=unit.difficulty,
        style=style,
        answer_length=answer_length,
        notes=notes,
        card_target=card_target,
        question_target=question_target,
        pedagogy_digest=pedagogy_digest,
    )
    batch_context = truncate_context(context_prompt, pedagogy_digest=pedagogy_digest)

    if progress:
        progress("planning")
    plan_result = _complete_with_retry(
        prompt=context_prompt,
        provider=name,
        system=PLAN_SYSTEM,
        model=model,
        num_predict=_PLAN_NUM_PREDICT,
        label="plan",
    )
    categories = _normalize_plan_counts(
        _parse_plan(plan_result["text"]),
        card_target=card_target,
        question_target=question_target,
        math_focus=math_focus,
        focus_group=focus_group,
    )
    _log.info(
        "generate_interactive plan_done unit_id=%s categories=%d duration_ms=%d",
        unit_id,
        len(categories),
        int((time.monotonic() - t0) * 1000),
    )

    modules: list[dict] = []
    all_card_questions: list[str] = []
    all_quiz_questions: list[str] = []

    for index, cat in enumerate(categories):
        if progress:
            progress(
                "category",
                index=index + 1,
                total=len(categories),
                category=cat["name"],
            )
        _log.info(
            "generate_interactive category_start unit_id=%s index=%d name=%s cards=%d questions=%d",
            unit_id,
            index + 1,
            cat["name"],
            cat["cards"],
            cat["questions"],
        )
        cards = _generate_category_cards(
            batch_context=batch_context,
            cat=cat,
            unit_id=unit_id,
            category_index=index,
            all_card_questions=all_card_questions,
            focus_group=focus_group,
            name=name,
            model=model,
        )
        all_card_questions.extend(c["question"] for c in cards)

        knowledge = _generate_knowledge(
            batch_context=batch_context,
            cat=cat,
            cards=cards,
            provider=name,
            model=model,
            index=index,
        )

        basiswissen = _generate_basiswissen(
            batch_context=batch_context,
            cat=cat,
            knowledge=knowledge,
            cards=cards,
            provider=name,
            model=model,
            index=index,
            focus_group=focus_group,
        )

        quiz_prompt = build_interactive_quiz_prompt(
            context=batch_context,
            category_name=cat["name"],
            category_focus=cat["focus"],
            count=cat["questions"],
            card_summaries=[f"{c['question']} → {c['answer'][:80]}" for c in cards[:6]],
            existing_questions=all_card_questions + all_quiz_questions,
        )
        quiz_result = _complete_with_retry(
            prompt=quiz_prompt,
            provider=name,
            system=QUIZ_SYSTEM,
            model=model,
            num_predict=_BATCH_NUM_PREDICT,
            label=f"quiz_{index + 1}",
        )
        questions = _parse_questions(quiz_result["text"], cat["questions"])
        all_quiz_questions.extend(q["q"] for q in questions)

        module_content = {
            "intro": cat["focus"] or "",
            "knowledge": knowledge,
            "cards": cards,
            "basiswissen": basiswissen,
        }
        module_quiz = {"questions": questions}
        module_content, module_quiz = enrich_module_with_basiswissen(
            content=module_content,
            quiz=module_quiz,
            basiswissen=basiswissen,
            question_count=cat["questions"],
            category_label=cat["name"],
            pedagogy=pedagogy_profile,
        )

        modules.append(
            {
                "title": cat["name"],
                "content": module_content,
                "quiz": module_quiz,
            }
        )
        _log.info(
            "generate_interactive category_done unit_id=%s index=%d cards=%d questions=%d",
            unit_id,
            index + 1,
            len(cards),
            len(questions),
        )

    modules, dedupe_warnings = dedupe_interactive_modules(modules)
    for warning in dedupe_warnings:
        _log.warning("generate_interactive dedupe unit_id=%s %s", unit_id, warning)

    log_pedagogy_coverage_warnings(modules, pedagogy_profile, unit_id=str(unit_id))
    enforce_label_coverage(modules, pedagogy_profile)

    for module in modules:
        quiz = module.get("quiz") if isinstance(module, dict) else None
        if isinstance(module, dict) and isinstance(quiz, dict):
            module["quiz"] = repair_quiz_block(quiz)

    try:
        validate_interactive_modules(
            modules,
            min_cards=_MIN_CARDS,
            min_questions=_MIN_QUESTIONS,
        )
    except LlmError:
        if len(modules) >= 4:
            total_cards = sum(len(m["content"]["cards"]) for m in modules)
            total_questions = sum(len(m["quiz"]["questions"]) for m in modules)
            if progress:
                progress("saving", cards=total_cards, questions=total_questions)
            _save_generated_modules(
                db,
                unit,
                modules,
                result_meta=plan_result,
                task="interactive",
                final=False,
            )
            db.commit()
        raise

    total_cards = sum(len(m["content"]["cards"]) for m in modules)
    total_questions = sum(len(m["quiz"]["questions"]) for m in modules)

    if progress:
        progress("saving", cards=total_cards, questions=total_questions)
    _save_generated_modules(
        db,
        unit,
        modules,
        result_meta=plan_result,
        task="interactive",
        final=True,
    )
    _log.info(
        "generate_interactive done unit_id=%s modules=%d cards=%d questions=%d total_ms=%d",
        unit_id,
        len(modules),
        total_cards,
        total_questions,
        int((time.monotonic() - t0) * 1000),
    )
    if progress:
        progress("done", cards=total_cards, questions=total_questions, modules=len(modules))
    return _dec_unit(unit)


def backfill_basiswissen_for_unit(
    db: Session,
    user: User,
    unit_id: uuid.UUID,
    *,
    provider: str | None = None,
    force: bool = False,
) -> dict:
    """Ergänzt oder erneuert strukturiertes Basiswissen in bestehenden interaktiven Modulen."""
    from app.ai.subject_focus import detect_focus_group
    from app.core.solution_repair import repair_generated_module
    from app.services.crypto_json import encrypt_json
    from app.services.unit_service import UnitError

    unit = _get_unit_or_404(db, user, unit_id)
    if str(unit.task_type or "") != "interactive":
        raise UnitError("Basiswissen nur für interaktive Lerneinheiten verfügbar.", "invalid_task")
    if not unit.modules:
        raise UnitError("Keine Module zum Ergänzen.", "no_modules")

    prefs = resolve_prefs_for_profile(db, unit.profile_id) or get_user_settings(user)
    name, model = resolve_provider(provider or prefs.get("ai_provider"))
    focus_group = (
        detect_focus_group(subject=unit.subject, task_type=str(unit.task_type or "interactive"))
        or "general"
    )

    record = db.query(LearningRecord).filter(LearningRecord.unit_id == unit.id).first()
    recon = decrypt_json(record.reconstruction_encrypted) if record and record.reconstruction_encrypted else {}
    notes = _collect_source_notes(db, unit, prefs)
    pedagogy_profile = collect_pedagogy_from_unit_sources(unit.sources, focus_group=focus_group)
    pedagogy_digest = build_pedagogy_digest(pedagogy_profile)
    title = decrypt_text_master(unit.title_encrypted)
    brief = decrypt_text_master(unit.brief_encrypted) if unit.brief_encrypted else ""
    trainer_opts = get_trainer_options(recon if isinstance(recon, dict) else {})
    context_prompt = build_interactive_plan_prompt(
        title=title,
        brief=brief,
        subject=unit.subject,
        math_focus=None,
        language=unit.language,
        target_age=unit.target_age,
        difficulty=unit.difficulty,
        style=str(trainer_opts.get("style") or "mixed"),
        answer_length=str(trainer_opts.get("answer_length") or "short"),
        notes=notes,
        card_target=_MIN_CARDS,
        question_target=_MIN_QUESTIONS,
        pedagogy_digest=pedagogy_digest,
    )
    batch_context = truncate_context(context_prompt, pedagogy_digest=pedagogy_digest)

    updated = 0
    skipped = 0
    for module in sorted(unit.modules, key=lambda m: m.order_index):
        content = decrypt_json(module.content_encrypted) or {}
        quiz = decrypt_json(module.quiz_encrypted) or {}
        if not isinstance(content, dict):
            skipped += 1
            continue
        existing = content.get("basiswissen")
        if (
            not force
            and isinstance(existing, dict)
            and (existing.get("concepts") or existing.get("cloze_templates"))
        ):
            skipped += 1
            continue

        quiz_dict = quiz if isinstance(quiz, dict) else {"questions": []}
        content, quiz_dict = strip_basiswissen_derivatives(content, quiz_dict)
        cards = [c for c in (content.get("cards") or []) if isinstance(c, dict)]
        knowledge = [k for k in (content.get("knowledge") or []) if isinstance(k, dict)]
        domain = decrypt_text_master(module.title_encrypted)
        cat = {"name": domain, "focus": str(content.get("intro") or "")[:300]}
        question_count = len(quiz_dict.get("questions") or [])

        basiswissen = _generate_basiswissen(
            batch_context=batch_context,
            cat=cat,
            knowledge=knowledge,
            cards=cards,
            provider=name,
            model=model,
            index=module.order_index,
            focus_group=focus_group,
        )
        content, quiz_dict = enrich_module_with_basiswissen(
            content=content,
            quiz=quiz_dict,
            basiswissen=basiswissen,
            question_count=max(question_count, 3),
            category_label=domain,
            pedagogy=pedagogy_profile,
        )
        repaired = repair_generated_module({"content": content, "quiz": quiz_dict})
        content = repaired.get("content") if isinstance(repaired.get("content"), dict) else content
        quiz_dict = repair_quiz_block(repaired.get("quiz") if isinstance(repaired.get("quiz"), dict) else quiz_dict)
        module.content_encrypted = encrypt_json(content)
        module.quiz_encrypted = encrypt_json(quiz_dict)
        updated += 1

    if updated:
        db.flush()
    _log.info(
        "backfill_basiswissen unit_id=%s updated=%d skipped=%d focus_group=%s",
        unit_id,
        updated,
        skipped,
        focus_group,
    )
    return {"updated_modules": updated, "skipped_modules": skipped, "focus_group": focus_group}
