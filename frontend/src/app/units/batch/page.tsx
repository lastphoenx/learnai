"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AppHeader } from "@/components/AppHeader";
import { BatchPdfPageGrid } from "@/components/BatchPdfPageGrid";
import { LearnerMultiSelect } from "@/components/LearnerMultiSelect";
import { useChildPreview } from "@/lib/childPreview";
import {
  fetchMe,
  fetchProfiles,
  fetchUnitTaskTypes,
  startBatchImport,
  type BatchImportPayload,
  type LearnerProfile,
  type User,
} from "@/lib/api";
import {
  detectFocusGroup,
  FALLBACK_FOCUS_GROUPS,
  focusGroupLabel,
  focusOptionsForGroup,
  showSubjectFocus,
  type FocusGroup,
} from "@/lib/subjectFocus";
import {
  FALLBACK_TRAINER_PRESETS,
  presetById,
  type TrainerPresetDefinition,
  type TrainerPresetId,
} from "@/lib/trainerPresets";

const MAX_PDF_BYTES = 50 * 1024 * 1024;

type WizardRow = {
  localId: string;
  title: string;
  pageFrom: number;
  pageTo: number;
  posten: string;
  preset: TrainerPresetId | "";
};

function newRow(partial?: Partial<WizardRow>): WizardRow {
  return {
    localId: crypto.randomUUID(),
    title: "",
    pageFrom: 1,
    pageTo: 2,
    posten: "",
    preset: "",
    ...partial,
  };
}

function pageRange(start: number, end: number): number[] {
  if (start < 1 || end < start) return [];
  return Array.from({ length: end - start + 1 }, (_, i) => start + i);
}

export default function BatchImportWizardPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [user, setUser] = useState<User | null>(null);
  const { asChild } = useChildPreview(user);
  const [profiles, setProfiles] = useState<LearnerProfile[]>([]);
  const [profileIds, setProfileIds] = useState<string[]>([]);
  const [focusGroups, setFocusGroups] = useState<FocusGroup[]>(FALLBACK_FOCUS_GROUPS);
  const [trainerPresets, setTrainerPresets] = useState<TrainerPresetDefinition[]>(FALLBACK_TRAINER_PRESETS);

  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [subject, setSubject] = useState("NMG");
  const [mathFocus, setMathFocus] = useState("nmg_history");
  const [targetAge, setTargetAge] = useState("");
  const [language, setLanguage] = useState("de");
  const [difficulty, setDifficulty] = useState(1);
  const [defaultPreset, setDefaultPreset] = useState<TrainerPresetId>("posten_compact");

  const [introFrom, setIntroFrom] = useState(1);
  const [introTo, setIntroTo] = useState(5);
  const [rows, setRows] = useState<WizardRow[]>([]);
  const [activeRowIndex, setActiveRowIndex] = useState<number | null>(0);
  const [rangeAnchor, setRangeAnchor] = useState<number | null>(null);

  const [assistStartPage, setAssistStartPage] = useState(6);
  const [assistCount, setAssistCount] = useState(12);
  const [assistFirstPosten, setAssistFirstPosten] = useState(14);

  const [sharedBriefText, setSharedBriefText] = useState("");
  const [includeReview, setIncludeReview] = useState(false);
  const [reviewTitle, setReviewTitle] = useState("Lernzielkontrolle");
  const [reviewFrom, setReviewFrom] = useState(1);
  const [reviewTo, setReviewTo] = useState(5);

  const [error, setError] = useState<string | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);

  const mathFocusVisible = showSubjectFocus("interactive", subject);
  const focusGroupId = detectFocusGroup(subject, "interactive");
  const focusOptions = focusOptionsForGroup(focusGroupId, focusGroups);
  const focusGroupName = focusGroupLabel(focusGroupId, focusGroups);
  const presetHint = presetById(trainerPresets, defaultPreset).hint;

  const unitCountPreview = rows.length + (includeReview ? 1 : 0);

  const rowPayload = useMemo(
    () =>
      rows.map((row) => ({
        pageFrom: row.pageFrom,
        pageTo: row.pageTo,
      })),
    [rows],
  );

  useEffect(() => {
    fetchMe()
      .then((u) => {
        setUser(u);
        if (u.must_enroll_2fa) window.location.href = "/settings";
        if (u.is_child && u.profile_id) {
          setProfileIds([u.profile_id]);
        } else if (!u.is_child) {
          fetchProfiles()
            .then((list) => {
              setProfiles(list);
              const children = list.filter((p) => p.is_child_profile);
              if (children.length === 1) setProfileIds([children[0].id]);
              else if (children.length > 1) setProfileIds(children.map((c) => c.id));
              else if (list[0]) setProfileIds([list[0].id]);
            })
            .catch(() => undefined);
        }
      })
      .catch(() => setAuthError("Nicht angemeldet"));
    fetchUnitTaskTypes()
      .then((data) => {
        if (data.focus_groups?.length) setFocusGroups(data.focus_groups);
        if (data.trainer_presets?.length) {
          setTrainerPresets(data.trainer_presets as TrainerPresetDefinition[]);
        }
      })
      .catch(() => undefined);
  }, []);

  function onPdfSelected(file: File | null) {
    setError(null);
    if (!file) {
      setPdfFile(null);
      return;
    }
    if (file.size > MAX_PDF_BYTES) {
      setError("PDF ist grösser als 50 MB.");
      return;
    }
    if (!file.name.toLowerCase().endsWith(".pdf") && file.type !== "application/pdf") {
      setError("Bitte eine PDF-Datei wählen.");
      return;
    }
    setPdfFile(file);
  }

  function applyDoublePageAssist() {
    if (assistCount < 1 || assistStartPage < 1) {
      setError("Assistent: gültige Startseite und Anzahl nötig.");
      return;
    }
    const generated: WizardRow[] = [];
    for (let i = 0; i < assistCount; i += 1) {
      const pageFrom = assistStartPage + i * 2;
      const posten = assistFirstPosten + i;
      generated.push(
        newRow({
          title: `Posten ${posten}`,
          pageFrom,
          pageTo: pageFrom + 1,
          posten: String(posten),
        }),
      );
    }
    setRows(generated);
    setActiveRowIndex(0);
    setError(null);
  }

  function onPageClick(page: number) {
    if (activeRowIndex == null || activeRowIndex < 0 || activeRowIndex >= rows.length) return;
    setRows((prev) => {
      const next = [...prev];
      const row = { ...next[activeRowIndex] };
      if (rangeAnchor == null) {
        row.pageFrom = page;
        row.pageTo = page;
        next[activeRowIndex] = row;
        setRangeAnchor(page);
        return next;
      }
      const from = Math.min(rangeAnchor, page);
      const to = Math.max(rangeAnchor, page);
      row.pageFrom = from;
      row.pageTo = to;
      if (!row.title.trim() && row.posten.trim()) {
        row.title = `Posten ${row.posten.trim()}`;
      }
      next[activeRowIndex] = row;
      return next;
    });
    if (rangeAnchor != null) setRangeAnchor(null);
  }

  function validateStep1(): string | null {
    if (!pdfFile) return "Bitte eine PDF hochladen.";
    if (!asChild && profiles.some((p) => p.is_child_profile) && profileIds.length === 0) {
      return "Bitte mindestens ein Kind auswählen.";
    }
    return null;
  }

  function validateStep2(): string | null {
    if (rows.length === 0) return "Mindestens eine Lerneinheit anlegen.";
    for (let i = 0; i < rows.length; i += 1) {
      const row = rows[i];
      if (!row.title.trim()) return `Zeile ${i + 1}: Titel fehlt.`;
      if (row.pageFrom < 1 || row.pageTo < row.pageFrom) return `Zeile ${i + 1}: ungültiger Seitenbereich.`;
    }
    if (introFrom > introTo || introFrom < 1) return "Intro-Seitenbereich ungültig.";
    return null;
  }

  function buildPayload(): BatchImportPayload {
    return {
      subject: subject.trim() || undefined,
      math_focus: mathFocusVisible && mathFocus ? mathFocus : undefined,
      target_age: targetAge.trim() || undefined,
      language,
      difficulty,
      task_type: "interactive",
      default_preset: defaultPreset,
      profile_id: user?.is_child && user.profile_id ? user.profile_id : undefined,
      profile_ids: !user?.is_child && profileIds.length > 0 ? profileIds : undefined,
      shared_brief_pages: pageRange(introFrom, introTo),
      shared_brief_text: sharedBriefText.trim() || undefined,
      units: rows.map((row) => ({
        title: row.title.trim(),
        page_from: row.pageFrom,
        page_to: row.pageTo,
        posten: row.posten.trim() && Number(row.posten) > 0 ? Number(row.posten) : undefined,
        preset: row.preset || undefined,
      })),
      review_unit: includeReview
        ? {
            title: reviewTitle.trim() || "Lernzielkontrolle",
            page_from: reviewFrom,
            page_to: reviewTo,
            preset: "exam_review",
          }
        : undefined,
    };
  }

  async function onStartBatch(e: FormEvent) {
    e.preventDefault();
    if (starting || !pdfFile) return;
    const err = validateStep2();
    if (err) {
      setError(err);
      return;
    }
    setError(null);
    setStarting(true);
    try {
      const result = await startBatchImport(pdfFile, buildPayload());
      router.push(`/units/batch/${result.batch_job_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Batch-Start fehlgeschlagen");
    } finally {
      setStarting(false);
    }
  }

  if (authError && !user) {
    return (
      <main className="shell">
        <p>{authError}</p>
        <Link href="/login">Zum Login</Link>
      </main>
    );
  }

  return (
    <main className="shell shell-wide">
      <AppHeader user={user} title="Mehrere Einheiten aus PDF" />
      <nav className="batch-wizard-steps card" aria-label="Wizard-Schritte">
        {[1, 2, 3].map((n) => (
          <button
            key={n}
            type="button"
            className={`batch-wizard-step${step === n ? " active" : step > n ? " done" : ""}`}
            onClick={() => {
              if (n === 2 && validateStep1()) {
                setError(validateStep1());
                return;
              }
              if (n === 3 && validateStep2()) {
                setError(validateStep2());
                return;
              }
              setError(null);
              setStep(n);
            }}
          >
            {n === 1 ? "PDF & Meta" : n === 2 ? "Seiten zuweisen" : "Start"}
          </button>
        ))}
      </nav>

      {error && (
        <p className="err" role="alert">
          {error}
        </p>
      )}

      {step === 1 && (
        <section className="card stack">
          <p className="muted" style={{ margin: 0 }}>
            Ein Heft-PDF hochladen, Metadaten setzen — im nächsten Schritt Posten/Doppelseiten zuordnen.
          </p>
          <label>
            PDF-Heft (max. 50 MB)
            <input
              type="file"
              accept="application/pdf,.pdf"
              onChange={(e) => onPdfSelected(e.target.files?.[0] ?? null)}
            />
          </label>
          {pdfFile && (
            <p className="muted" style={{ margin: 0 }}>
              {pdfFile.name} ({Math.round(pdfFile.size / 1024 / 1024)} MB)
            </p>
          )}
          <label>
            Fach / Thema
            <input value={subject} maxLength={64} onChange={(e) => setSubject(e.target.value)} />
          </label>
          {mathFocusVisible && (
            <label>
              Schwerpunkt{focusGroupName ? ` — ${focusGroupName}` : ""}
              <select value={mathFocus} onChange={(e) => setMathFocus(e.target.value)}>
                <option value="">— optional —</option>
                {(focusGroupId ? focusOptions : focusGroups.flatMap((g) => g.options)).map((o) => (
                  <option key={o.key} value={o.key}>
                    {o.label}
                  </option>
                ))}
              </select>
            </label>
          )}
          <label>
            Zielalter
            <input value={targetAge} maxLength={32} onChange={(e) => setTargetAge(e.target.value)} placeholder="z. B. 11–12" />
          </label>
          <label>
            Sprache
            <select value={language} onChange={(e) => setLanguage(e.target.value)}>
              <option value="de">Deutsch</option>
              <option value="fr">Französisch</option>
              <option value="it">Italienisch</option>
              <option value="en">Englisch</option>
            </select>
          </label>
          <label>
            Umfangs-Preset (Standard pro Posten)
            <select value={defaultPreset} onChange={(e) => setDefaultPreset(e.target.value as TrainerPresetId)}>
              {trainerPresets.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label}
                </option>
              ))}
            </select>
          </label>
          <p className="muted" style={{ margin: 0, fontSize: "0.9rem" }}>
            {presetHint}
          </p>
          {!asChild && profiles.length > 0 && (
            <LearnerMultiSelect
              profiles={profiles}
              selectedIds={profileIds}
              onChange={setProfileIds}
              label="Für welches Kind?"
            />
          )}
          <label>
            Schwierigkeit (1–5)
            <input
              type="number"
              min={1}
              max={5}
              value={difficulty}
              onChange={(e) => setDifficulty(Number(e.target.value))}
            />
          </label>
          <div className="batch-wizard-actions">
            <Link className="btn ghost" href="/units">
              Abbrechen
            </Link>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => {
                const err = validateStep1();
                if (err) {
                  setError(err);
                  return;
                }
                setError(null);
                setStep(2);
              }}
            >
              Weiter — Seiten zuweisen
            </button>
          </div>
        </section>
      )}

      {step === 2 && pdfFile && (
        <section className="stack">
          <div className="card stack">
            <h2 style={{ margin: 0 }}>Intro-Seiten (shared brief)</h2>
            <p className="muted" style={{ margin: 0 }}>
              Diese PDF-Seiten werden nicht als eigene Einheit importiert, sondern als gemeinsamer Kontext für alle
              Posten.
            </p>
            <div className="form-row">
              <label>
                Von Seite
                <input type="number" min={1} value={introFrom} onChange={(e) => setIntroFrom(Number(e.target.value))} />
              </label>
              <label>
                Bis Seite
                <input type="number" min={1} value={introTo} onChange={(e) => setIntroTo(Number(e.target.value))} />
              </label>
            </div>
          </div>

          <div className="card stack">
            <div className="section-head">
              <h2 style={{ margin: 0 }}>Lerneinheiten</h2>
              <button
                type="button"
                className="btn-sm"
                onClick={() => {
                  setRows((prev) => [...prev, newRow()]);
                  setActiveRowIndex(rows.length);
                }}
              >
                Zeile hinzufügen
              </button>
            </div>
            <div className="batch-assist card stack" style={{ background: "var(--bg-2)" }}>
              <p className="muted" style={{ margin: 0 }}>
                Doppelseiten-Assistent (1 Doppelseite ≈ 1 Posten)
              </p>
              <div className="form-row">
                <label>
                  Erste PDF-Seite
                  <input
                    type="number"
                    min={1}
                    value={assistStartPage}
                    onChange={(e) => setAssistStartPage(Number(e.target.value))}
                  />
                </label>
                <label>
                  Anzahl Posten
                  <input
                    type="number"
                    min={1}
                    max={30}
                    value={assistCount}
                    onChange={(e) => setAssistCount(Number(e.target.value))}
                  />
                </label>
                <label>
                  Erste Posten-Nr.
                  <input
                    type="number"
                    min={1}
                    value={assistFirstPosten}
                    onChange={(e) => setAssistFirstPosten(Number(e.target.value))}
                  />
                </label>
              </div>
              <button type="button" className="btn-sm" onClick={applyDoublePageAssist}>
                Zeilen erzeugen
              </button>
            </div>
            <div className="batch-rows">
              {rows.map((row, index) => (
                <div
                  key={row.localId}
                  className={`batch-row card${activeRowIndex === index ? " batch-row-active" : ""}`}
                >
                  <button
                    type="button"
                    className="batch-row-select"
                    onClick={() => {
                      setActiveRowIndex(index);
                      setRangeAnchor(null);
                    }}
                  >
                    Zeile {index + 1}
                  </button>
                  <label>
                    Titel
                    <input
                      value={row.title}
                      onChange={(e) =>
                        setRows((prev) => {
                          const next = [...prev];
                          next[index] = { ...next[index], title: e.target.value };
                          return next;
                        })
                      }
                    />
                  </label>
                  <label>
                    Posten-Nr.
                    <input
                      type="number"
                      min={1}
                      value={row.posten}
                      onChange={(e) =>
                        setRows((prev) => {
                          const next = [...prev];
                          next[index] = { ...next[index], posten: e.target.value };
                          return next;
                        })
                      }
                    />
                  </label>
                  <label>
                    Seiten von
                    <input
                      type="number"
                      min={1}
                      value={row.pageFrom}
                      onChange={(e) =>
                        setRows((prev) => {
                          const next = [...prev];
                          next[index] = { ...next[index], pageFrom: Number(e.target.value) };
                          return next;
                        })
                      }
                    />
                  </label>
                  <label>
                    bis
                    <input
                      type="number"
                      min={1}
                      value={row.pageTo}
                      onChange={(e) =>
                        setRows((prev) => {
                          const next = [...prev];
                          next[index] = { ...next[index], pageTo: Number(e.target.value) };
                          return next;
                        })
                      }
                    />
                  </label>
                  <label>
                    Preset
                    <select
                      value={row.preset}
                      onChange={(e) =>
                        setRows((prev) => {
                          const next = [...prev];
                          next[index] = { ...next[index], preset: e.target.value as TrainerPresetId | "" };
                          return next;
                        })
                      }
                    >
                      <option value="">Standard ({defaultPreset})</option>
                      {trainerPresets.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <button
                    type="button"
                    className="btn-sm ghost"
                    onClick={() => {
                      setRows((prev) => prev.filter((_, i) => i !== index));
                      setActiveRowIndex((prev) => (prev === index ? null : prev != null && prev > index ? prev - 1 : prev));
                    }}
                  >
                    Entfernen
                  </button>
                </div>
              ))}
            </div>
            <p className="muted" style={{ margin: 0 }}>
              Vorschau: <strong>{rows.length}</strong> Lerneinheit{rows.length === 1 ? "" : "en"}
              {includeReview ? " + Review" : ""}. Aktive Zeile im Raster anklicken: 1. Klick = Startseite, 2. Klick =
              Endseite.
            </p>
          </div>

          <div className="card stack">
            <h2 style={{ margin: 0 }}>PDF-Seiten</h2>
            <BatchPdfPageGrid
              file={pdfFile}
              introFrom={introFrom}
              introTo={introTo}
              activeRowIndex={activeRowIndex}
              rows={rowPayload}
              onPageClick={onPageClick}
            />
          </div>

          <div className="batch-wizard-actions card">
            <button type="button" className="btn ghost" onClick={() => setStep(1)}>
              Zurück
            </button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => {
                const err = validateStep2();
                if (err) {
                  setError(err);
                  return;
                }
                setError(null);
                setStep(3);
              }}
            >
              Weiter — prüfen & starten
            </button>
          </div>
        </section>
      )}

      {step === 3 && pdfFile && (
        <form className="card stack" onSubmit={onStartBatch}>
          <h2 style={{ margin: 0 }}>Batch starten</h2>
          <p className="muted" style={{ margin: 0 }}>
            Es werden <strong>{unitCountPreview}</strong> Lerneinheit{unitCountPreview === 1 ? "" : "en"} angelegt und
            nacheinander generiert (kann 1–3 Stunden dauern).
          </p>
          <label>
            Gemeinsamer Auftrag (optional, überschreibt Intro-Vision)
            <textarea
              rows={5}
              value={sharedBriefText}
              onChange={(e) => setSharedBriefText(e.target.value)}
              placeholder="Leer lassen = Intro-Seiten als Kontext extrahieren"
            />
          </label>
          <label style={{ display: "flex", gap: 8, alignItems: "center", fontWeight: 600 }}>
            <input type="checkbox" checked={includeReview} onChange={(e) => setIncludeReview(e.target.checked)} />
            Review-Einheit (Lernzielkontrolle) hinzufügen
          </label>
          {includeReview && (
            <div className="form-row">
              <label>
                Review-Titel
                <input value={reviewTitle} onChange={(e) => setReviewTitle(e.target.value)} />
              </label>
              <label>
                Seiten von
                <input type="number" min={1} value={reviewFrom} onChange={(e) => setReviewFrom(Number(e.target.value))} />
              </label>
              <label>
                bis
                <input type="number" min={1} value={reviewTo} onChange={(e) => setReviewTo(Number(e.target.value))} />
              </label>
            </div>
          )}
          <ul className="batch-summary-list">
            {rows.map((row) => (
              <li key={row.localId}>
                {row.title.trim() || "Ohne Titel"} — PDF S. {row.pageFrom}–{row.pageTo}
                {row.posten ? ` (Posten ${row.posten})` : ""}
              </li>
            ))}
            {includeReview && (
              <li>
                {reviewTitle.trim()} — PDF S. {reviewFrom}–{reviewTo} (exam_review)
              </li>
            )}
          </ul>
          <div className="batch-wizard-actions">
            <button type="button" className="btn ghost" onClick={() => setStep(2)}>
              Zurück
            </button>
            <button type="submit" className="btn btn-primary" disabled={starting}>
              {starting ? "Batch wird gestartet…" : "Batch starten"}
            </button>
          </div>
        </form>
      )}
    </main>
  );
}
