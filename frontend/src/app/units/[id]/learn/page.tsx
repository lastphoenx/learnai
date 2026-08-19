"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { AppHeader } from "@/components/AppHeader";
import {
  completeLearn,
  fetchLearnState,
  fetchMe,
  markLearnTextRead,
  resetLearnProgress,
  saveLearnPosition,
  speak,
  submitLearnAnswer,
  type LearnModule,
  type LearnProgress,
  type LearnState,
  type LearnSummary,
  type User,
} from "@/lib/api";

type AnswerResult = {
  correct: boolean;
  correct_index: number;
  explanation?: string;
  module_quiz_done: boolean;
};

export default function UnitLearnPage() {
  const params = useParams();
  const unitId = params.id as string;
  const [user, setUser] = useState<User | null>(null);
  const [state, setState] = useState<LearnState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [answerResult, setAnswerResult] = useState<AnswerResult | null>(null);
  const [selectedOption, setSelectedOption] = useState<number | null>(null);

  const load = useCallback(() => {
    fetchLearnState(unitId)
      .then((s) => {
        setState(s);
        setAnswerResult(null);
        setSelectedOption(null);
      })
      .catch((e: Error) => setError(e.message));
  }, [unitId]);

  useEffect(() => {
    fetchMe()
      .then(setUser)
      .catch(() => setError("Nicht angemeldet"));
    load();
  }, [load]);

  async function goTo(
    moduleIndex: number,
    phase: LearnProgress["phase"],
    questionIndex = 0,
  ) {
    if (!state) return;
    setBusy(true);
    setError(null);
    try {
      const res = await saveLearnPosition(unitId, {
        module_index: moduleIndex,
        phase,
        question_index: questionIndex,
      });
      setState({
        ...state,
        progress: res.progress,
        summary: res.summary,
      });
      setAnswerResult(null);
      setSelectedOption(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Speichern fehlgeschlagen");
    } finally {
      setBusy(false);
    }
  }

  async function onResetLearn() {
    if (!confirm("Fortschritt zurücksetzen und von vorne beginnen?")) return;
    setBusy(true);
    setError(null);
    try {
      const res = await resetLearnProgress(unitId);
      if (state) {
        setState({ ...state, progress: res.progress, summary: res.summary });
      } else {
        load();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Zurücksetzen fehlgeschlagen");
    } finally {
      setBusy(false);
    }
  }

  async function onResume() {
    if (!state) return;
    for (let i = 0; i < state.modules.length; i++) {
      const m = state.modules[i];
      const prog = state.progress.modules[m.id];
      if (prog?.done) continue;
      const hasText = Boolean(m.content?.text?.trim());
      const hasQuiz = (m.quiz?.questions?.length || 0) > 0;
      if (hasText && !prog?.text_read) {
        await goTo(i, "read");
        return;
      }
      if (hasQuiz) {
        const answers = prog?.answers || [];
        const nextQ = answers.findIndex((a) => a === null || a === undefined);
        await goTo(i, "quiz", nextQ >= 0 ? nextQ : 0);
        return;
      }
      await goTo(i, "module_done");
      return;
    }
    await onStart();
  }

  async function onStart() {
    const mod = state?.modules[0];
    if (!mod) return;
    const hasText = Boolean(mod.content?.text?.trim());
    const hasQuiz = (mod.quiz?.questions?.length || 0) > 0;
    if (hasText) {
      await goTo(0, "read");
    } else if (hasQuiz) {
      await goTo(0, "quiz", 0);
    } else {
      await goTo(0, "module_done");
    }
  }

  async function onTextContinue() {
    if (!state) return;
    const mod = currentModule(state);
    if (!mod) return;
    setBusy(true);
    try {
      const res = await markLearnTextRead(unitId, mod.id);
      setState({ ...state, progress: res.progress, summary: res.summary });
      const hasQuiz = (mod.quiz?.questions?.length || 0) > 0;
      if (hasQuiz) {
        await goTo(state.progress.module_index, "quiz", 0);
      } else {
        await goTo(state.progress.module_index, "module_done");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fehler");
    } finally {
      setBusy(false);
    }
  }

  async function onSelectAnswer(optionIndex: number) {
    if (!state || answerResult) return;
    const mod = currentModule(state);
    if (!mod) return;
    setSelectedOption(optionIndex);
    setBusy(true);
    try {
      const res = await submitLearnAnswer(unitId, {
        module_id: mod.id,
        question_index: state.progress.question_index,
        selected: optionIndex,
      });
      setState({ ...state, progress: res.progress, summary: res.summary });
      setAnswerResult({
        correct: res.correct,
        correct_index: res.correct_index,
        explanation: res.explanation,
        module_quiz_done: res.module_quiz_done,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Antwort fehlgeschlagen");
      setSelectedOption(null);
    } finally {
      setBusy(false);
    }
  }

  async function onQuizNext() {
    if (!state) return;
    const mod = currentModule(state);
    if (!mod) return;
    const questions = mod.quiz?.questions || [];
    const nextQ = state.progress.question_index + 1;
    if (nextQ < questions.length) {
      await goTo(state.progress.module_index, "quiz", nextQ);
    } else {
      await goTo(state.progress.module_index, "module_done");
    }
  }

  async function onModuleContinue() {
    if (!state) return;
    const nextIndex = state.progress.module_index + 1;
    if (nextIndex >= state.modules.length) {
      setBusy(true);
      try {
        const res = await completeLearn(unitId);
        setState({ ...state, progress: res.progress, summary: res.summary });
      } catch (err) {
        setError(err instanceof Error ? err.message : "Abschluss fehlgeschlagen");
      } finally {
        setBusy(false);
      }
      return;
    }
    const next = state.modules[nextIndex];
    const hasText = Boolean(next.content?.text?.trim());
    const hasQuiz = (next.quiz?.questions?.length || 0) > 0;
    if (hasText) {
      await goTo(nextIndex, "read");
    } else if (hasQuiz) {
      await goTo(nextIndex, "quiz", 0);
    } else {
      await goTo(nextIndex, "module_done");
    }
  }

  async function onBack() {
    if (!state) return;
    const { module_index, phase, question_index } = state.progress;
    if (phase === "read" && module_index === 0) {
      await goTo(0, "intro");
      return;
    }
    if (phase === "read") {
      const prev = state.modules[module_index - 1];
      const prevDone = state.progress.modules[prev.id]?.done;
      if (prevDone) {
        await goTo(module_index - 1, "module_done");
      } else {
        const prevQuiz = prev.quiz?.questions || [];
        if (prevQuiz.length > 0) {
          await goTo(module_index - 1, "quiz", prevQuiz.length - 1);
        } else if (prev.content?.text) {
          await goTo(module_index - 1, "read");
        } else {
          await goTo(module_index - 1, "module_done");
        }
      }
      return;
    }
    if (phase === "quiz" && question_index > 0) {
      await goTo(module_index, "quiz", question_index - 1);
      return;
    }
    if (phase === "quiz") {
      const mod = state.modules[module_index];
      if (mod.content?.text?.trim()) {
        await goTo(module_index, "read");
      } else if (module_index === 0) {
        await goTo(0, "intro");
      } else {
        await goTo(module_index - 1, "module_done");
      }
      return;
    }
    if (phase === "module_done") {
      const mod = state.modules[module_index];
      const questions = mod.quiz?.questions || [];
      if (questions.length > 0) {
        await goTo(module_index, "quiz", questions.length - 1);
      } else if (mod.content?.text?.trim()) {
        await goTo(module_index, "read");
      } else if (module_index === 0) {
        await goTo(0, "intro");
      } else {
        await goTo(module_index - 1, "module_done");
      }
    }
  }

  async function onSpeak(text: string, lang: string) {
    try {
      const blob = await speak(text, lang);
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audio.play();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Vorlesen nicht möglich");
    }
  }

  if (error && !state) {
    return (
      <main className="shell">
        <p className="err">{error}</p>
        <Link href={`/units/${unitId}`}>Zurück zur Einheit</Link>
      </main>
    );
  }

  if (!state) {
    return (
      <main className="shell">
        <p className="muted">Laden…</p>
      </main>
    );
  }

  const { unit, modules, progress, summary } = state;
  const mod = currentModule(state);
  const phase = progress.phase;
  const totalModules = modules.length;
  const stepNum =
    phase === "intro"
      ? 0
      : phase === "complete"
        ? totalModules + 1
        : progress.module_index + 1;

  return (
    <main className="shell">
      <AppHeader user={user} />
      <nav className="breadcrumb" aria-label="Brotkrumen">
        <Link href="/units">Einheiten</Link>
        <span aria-hidden="true">›</span>
        <Link href={`/units/${unit.id}`}>{unit.title}</Link>
        <span aria-hidden="true">›</span>
        <span>Lernen</span>
      </nav>
      <h1 className="unit-title" style={{ marginBottom: "1rem" }}>
        {unit.title}
      </h1>
      <div className="learn-step-label">
        {phase === "complete"
          ? "Abgeschlossen"
          : phase === "intro"
            ? "Einstieg"
            : `Block ${stepNum} von ${totalModules}`}
        {summary.percent > 0 && phase !== "complete" && (
          <span className="learn-badge" style={{ marginLeft: 8 }}>
            {summary.percent}% erledigt
          </span>
        )}
      </div>
      <div className="learn-progress-bar" aria-hidden>
        <div className="learn-progress-fill" style={{ width: `${summary.percent}%` }} />
      </div>

      {error && <p className="err">{error}</p>}

      <div className="card stack">
        {phase === "intro" && (
          <>
            <h2 style={{ margin: 0 }}>Bereit zum Lernen?</h2>
            {unit.brief && <p>{unit.brief}</p>}
            <p className="muted">
              {totalModules} Lernblock{totalModules !== 1 ? "e" : ""} · Stufe {unit.difficulty}
              {unit.subject ? ` · ${unit.subject}` : ""}
            </p>
            {summary.status === "in_progress" && summary.modules_done > 0 && (
              <p>
                Du hast schon {summary.modules_done} von {totalModules} Blöcken geschafft — weitermachen
                oder von vorne.
              </p>
            )}
            <div className="learn-actions">
              <button
                type="button"
                className="btn-primary"
                onClick={() => (summary.modules_done > 0 ? onResume() : onStart())}
                disabled={busy}
              >
                {summary.modules_done > 0 ? "Weitermachen" : "Los geht's"}
              </button>
              {summary.modules_done > 0 && (
                <button type="button" onClick={onResetLearn} disabled={busy}>
                  Von Anfang (zurücksetzen)
                </button>
              )}
              <Link href={`/units/${unitId}`} className="btn ghost">
                Pause · Zurück
              </Link>
            </div>
          </>
        )}

        {phase === "read" && mod && (
          <>
            <h2 style={{ margin: 0 }}>{mod.title}</h2>
            {mod.content?.text && (
              <p style={{ whiteSpace: "pre-wrap", fontSize: "1.05rem" }}>{mod.content.text}</p>
            )}
            <div className="learn-actions">
              <button type="button" onClick={onBack} disabled={busy}>
                Zurück
              </button>
              <button
                type="button"
                onClick={() => onSpeak(mod.content?.text || mod.title, unit.language)}
              >
                Vorlesen
              </button>
              <button type="button" className="btn-primary" onClick={onTextContinue} disabled={busy}>
                {(mod.quiz?.questions?.length || 0) > 0 ? "Weiter zum Quiz" : "Weiter"}
              </button>
              <Link href="/units" className="muted">
                Pause
              </Link>
            </div>
          </>
        )}

        {phase === "quiz" && mod && (
          <>
            <h2 style={{ margin: 0 }}>{mod.title}</h2>
            {(() => {
              const q = mod.quiz?.questions?.[progress.question_index];
              if (!q) return <p className="muted">Keine Frage.</p>;
              const saved = progress.modules[mod.id]?.answers?.[progress.question_index];
              return (
                <>
                  <p className="muted">
                    Frage {progress.question_index + 1} von {mod.quiz?.questions?.length}
                  </p>
                  <p style={{ fontWeight: 600, fontSize: "1.05rem" }}>{q.q}</p>
                  <div>
                    {(q.options || []).map((opt, i) => {
                      let cls = "learn-quiz-option";
                      if (answerResult) {
                        if (i === answerResult.correct_index) cls += " correct";
                        else if (i === selectedOption) cls += " wrong";
                      } else if (i === selectedOption) {
                        cls += " selected";
                      }
                      return (
                        <button
                          key={i}
                          type="button"
                          className={cls}
                          disabled={busy || Boolean(answerResult)}
                          onClick={() => onSelectAnswer(i)}
                        >
                          {opt}
                        </button>
                      );
                    })}
                  </div>
                  {answerResult && (
                    <p style={{ marginTop: "1rem" }}>
                      {answerResult.correct ? (
                        <strong style={{ color: "var(--accent)" }}>Richtig!</strong>
                      ) : (
                        <strong style={{ color: "var(--danger)" }}>Nicht ganz — schau nochmal hin.</strong>
                      )}
                      {answerResult.explanation && (
                        <span className="muted"> {answerResult.explanation}</span>
                      )}
                    </p>
                  )}
                  {saved !== null && saved !== undefined && !answerResult && (
                    <p className="muted">Bereits beantwortet.</p>
                  )}
                </>
              );
            })()}
            <div className="learn-actions">
              <button type="button" onClick={onBack} disabled={busy || Boolean(answerResult)}>
                Zurück
              </button>
              {answerResult && (
                <button type="button" className="btn-primary" onClick={onQuizNext} disabled={busy}>
                  {progress.question_index + 1 < (mod.quiz?.questions?.length || 0)
                    ? "Nächste Frage"
                    : "Block abschliessen"}
                </button>
              )}
              <Link href="/units" className="muted">
                Pause
              </Link>
            </div>
          </>
        )}

        {phase === "module_done" && mod && (
          <>
            <h2 style={{ margin: 0 }}>Block geschafft!</h2>
            <p>
              <strong>{mod.title}</strong> ist erledigt.
            </p>
            {progress.modules[mod.id]?.total ? (
              <p>
                Quiz: {progress.modules[mod.id].correct} von {progress.modules[mod.id].total} richtig.
              </p>
            ) : null}
            <div className="learn-actions">
              <button type="button" onClick={onBack} disabled={busy}>
                Zurück
              </button>
              <button type="button" className="btn-primary" onClick={onModuleContinue} disabled={busy}>
                {progress.module_index + 1 < totalModules ? "Nächster Block" : "Einheit abschliessen"}
              </button>
              <Link href="/units" className="muted">
                Pause
              </Link>
            </div>
          </>
        )}

        {phase === "complete" && (
          <>
            <h2 style={{ margin: 0 }}>Geschafft!</h2>
            <p>Du hast alle {totalModules} Blöcke durchgearbeitet.</p>
            {summary.quiz_total > 0 && (
              <p>
                Quiz gesamt: <strong>{summary.quiz_correct}</strong> von{" "}
                <strong>{summary.quiz_total}</strong> richtig (
                {Math.round((100 * summary.quiz_correct) / summary.quiz_total)}%).
              </p>
            )}
            <div className="learn-actions">
              <button type="button" className="btn-primary" onClick={onResetLearn} disabled={busy}>
                Nochmal lernen
              </button>
              <Link href="/units" className="btn">
                Andere Einheit
              </Link>
              <Link href={`/units/${unitId}`}>Zur Bearbeitung</Link>
              <Link href="/history">Verlauf</Link>
            </div>
          </>
        )}
      </div>
    </main>
  );
}

function currentModule(state: LearnState): LearnModule | null {
  return state.modules[state.progress.module_index] ?? null;
}
