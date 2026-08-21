"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  fetchUnitTaskTypes,
  patchUnit,
  type LearningUnit,
  type TrainerOptions,
  type UnitPatchBody,
} from "@/lib/api";
import { UnitFieldGuide } from "@/components/UnitFieldGuide";
import {
  FALLBACK_MATH_FOCUS,
  FALLBACK_TASK_TYPES,
  showMathFocus,
  type MathFocusOption,
  type UnitTaskType,
} from "@/lib/taskTypes";
import { getUnitFieldGuide } from "@/lib/unitFieldHints";

type Props = {
  unit: LearningUnit;
  open: boolean;
  onClose: () => void;
  onSaved: (unit: LearningUnit) => void;
};

export function UnitEditDialog({ unit, open, onClose, onSaved }: Props) {
  const [title, setTitle] = useState(unit.title);
  const [brief, setBrief] = useState(unit.brief || "");
  const [subject, setSubject] = useState(unit.subject || "");
  const [language, setLanguage] = useState(unit.language);
  const [targetAge, setTargetAge] = useState(unit.target_age || "");
  const [difficulty, setDifficulty] = useState(unit.difficulty);
  const [taskType, setTaskType] = useState(unit.task_type || "mixed");
  const [mathFocus, setMathFocus] = useState(unit.math_focus || "");
  const [trainerCards, setTrainerCards] = useState(unit.trainer_options?.cards ?? 50);
  const [trainerQuestions, setTrainerQuestions] = useState(unit.trainer_options?.questions ?? 50);
  const [trainerStyle, setTrainerStyle] = useState<TrainerOptions["style"]>(
    unit.trainer_options?.style ?? "playful",
  );
  const [trainerProvider, setTrainerProvider] = useState(unit.trainer_options?.llm_provider ?? "");
  const [taskTypes, setTaskTypes] = useState<UnitTaskType[]>(FALLBACK_TASK_TYPES);
  const [mathFocusOptions, setMathFocusOptions] = useState<MathFocusOption[]>(FALLBACK_MATH_FOCUS);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!open) return;
    setTitle(unit.title);
    setBrief(unit.brief || "");
    setSubject(unit.subject || "");
    setLanguage(unit.language);
    setTargetAge(unit.target_age || "");
    setDifficulty(unit.difficulty);
    setTaskType(unit.task_type || "mixed");
    setMathFocus(unit.math_focus || "");
    setTrainerCards(unit.trainer_options?.cards ?? 50);
    setTrainerQuestions(unit.trainer_options?.questions ?? 50);
    setTrainerStyle(unit.trainer_options?.style ?? "playful");
    setTrainerProvider(unit.trainer_options?.llm_provider ?? "");
    setError(null);
  }, [open, unit]);

  useEffect(() => {
    fetchUnitTaskTypes()
      .then((data) => {
        if (data.task_types?.length) setTaskTypes(data.task_types);
        if (data.math_focus?.length) setMathFocusOptions(data.math_focus);
      })
      .catch(() => undefined);
  }, []);

  const mathFocusVisible = showMathFocus(taskType, subject);
  const selectedType = taskTypes.find((t) => t.key === taskType);

  const fieldCtx = useMemo(
    () => ({ taskType, mathFocus, subject }),
    [taskType, mathFocus, subject],
  );
  const titleGuide = useMemo(() => getUnitFieldGuide("title", fieldCtx), [fieldCtx]);
  const briefGuide = useMemo(() => getUnitFieldGuide("brief", fieldCtx), [fieldCtx]);
  const subjectGuide = useMemo(() => getUnitFieldGuide("subject", fieldCtx), [fieldCtx]);
  const targetAgeGuide = useMemo(() => getUnitFieldGuide("targetAge", fieldCtx), [fieldCtx]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const body: UnitPatchBody = {
        title: title.trim(),
        brief: brief.trim() || null,
        subject: subject.trim() || null,
        language,
        target_age: targetAge.trim() || null,
        difficulty,
        task_type: taskType,
        math_focus: mathFocusVisible && mathFocus ? mathFocus : null,
      };
      if (taskType === "interactive") {
        body.trainer_options = {
          cards: trainerCards,
          questions: trainerQuestions,
          style: trainerStyle,
          answer_length: "short",
          llm_provider: trainerProvider.trim() || null,
        };
      }
      const next = await patchUnit(unit.id, body);
      onSaved(next);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Speichern fehlgeschlagen");
    } finally {
      setBusy(false);
    }
  }

  if (!open) return null;

  return (
    <div className="dialog-backdrop" role="presentation" onClick={onClose}>
      <div
        className="dialog card stack"
        role="dialog"
        aria-labelledby="unit-edit-title"
        aria-modal="true"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="dialog-header">
          <h2 id="unit-edit-title">Einheit bearbeiten</h2>
          <button type="button" className="icon-btn" onClick={onClose} aria-label="Schließen">
            ✕
          </button>
        </div>
        <form onSubmit={onSubmit} className="stack">
          <label className="unit-field-wrap">
            Titel
            <input
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder={titleGuide.placeholder}
            />
            <UnitFieldGuide tip={titleGuide.tip} show={!title.trim()} />
          </label>
          <label>
            Aufgabentyp
            <select value={taskType} onChange={(e) => setTaskType(e.target.value)}>
              {taskTypes.map((t) => (
                <option key={t.key} value={t.key}>
                  {t.label}
                </option>
              ))}
            </select>
          </label>
          {selectedType && <p className="muted" style={{ margin: 0, fontSize: "0.88rem" }}>{selectedType.description}</p>}
          {mathFocusVisible && (
            <label>
              Mathe-Schwerpunkt
              <select value={mathFocus} onChange={(e) => setMathFocus(e.target.value)}>
                {mathFocusOptions.map((o) => (
                  <option key={o.key || "none"} value={o.key}>
                    {o.label}
                  </option>
                ))}
              </select>
            </label>
          )}
          <label className="unit-field-wrap">
            Fach / Thema
            <input
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              placeholder={subjectGuide.placeholder}
            />
            <UnitFieldGuide tip={subjectGuide.tip} show={!subject.trim()} />
          </label>
          <label className="unit-field-wrap">
            Beschreibung / Auftrag an die KI
            <textarea
              value={brief}
              onChange={(e) => setBrief(e.target.value)}
              rows={8}
              placeholder={briefGuide.placeholder}
            />
            <UnitFieldGuide tip={briefGuide.tip} show={!brief.trim()} />
          </label>
          <div className="form-row">
            <label>
              Sprache
              <select value={language} onChange={(e) => setLanguage(e.target.value)}>
                <option value="de">Deutsch</option>
                <option value="fr">Französisch</option>
                <option value="it">Italienisch</option>
                <option value="en">Englisch</option>
              </select>
            </label>
            <label className="unit-field-wrap">
              Zielalter
              <input
                value={targetAge}
                onChange={(e) => setTargetAge(e.target.value)}
                placeholder={targetAgeGuide.placeholder}
              />
              <UnitFieldGuide tip={targetAgeGuide.tip} show={!targetAge.trim()} />
            </label>
            <label>
              Schwierigkeit
              <input
                type="number"
                min={1}
                max={5}
                value={difficulty}
                onChange={(e) => setDifficulty(Number(e.target.value))}
              />
            </label>
          </div>
          {taskType === "interactive" && (
            <div className="stack trainer-options-form">
              <p className="muted" style={{ margin: 0 }}>
                Lerntrainer — Ziele für die KI-Generierung
              </p>
              <div className="form-row">
                <label>
                  Lernkarten
                  <input
                    type="number"
                    min={30}
                    max={120}
                    value={trainerCards}
                    onChange={(e) => setTrainerCards(Number(e.target.value))}
                  />
                </label>
                <label>
                  Quizfragen
                  <input
                    type="number"
                    min={30}
                    max={120}
                    value={trainerQuestions}
                    onChange={(e) => setTrainerQuestions(Number(e.target.value))}
                  />
                </label>
                <label>
                  Stil
                  <select
                    value={trainerStyle}
                    onChange={(e) => setTrainerStyle(e.target.value as TrainerOptions["style"])}
                  >
                    <option value="playful">Spielerisch</option>
                    <option value="balanced">Ausgewogen</option>
                    <option value="factual">Sachlich</option>
                  </select>
                </label>
                <label>
                  KI-Provider
                  <select value={trainerProvider} onChange={(e) => setTrainerProvider(e.target.value)}>
                    <option value="">Profil-Standard</option>
                    <option value="ollama">Lokal (Ollama)</option>
                    <option value="openai">OpenAI</option>
                    <option value="anthropic">Anthropic</option>
                  </select>
                </label>
              </div>
            </div>
          )}
          {error && <p className="err">{error}</p>}
          <div className="dialog-actions">
            <button type="button" className="ghost" onClick={onClose} disabled={busy}>
              Abbrechen
            </button>
            <button type="submit" className="btn-primary" disabled={busy}>
              {busy ? "Speichern…" : "Speichern"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
