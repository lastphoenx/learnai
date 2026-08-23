"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { AppHeader } from "@/components/AppHeader";
import {
  deletePedagogyGoldenFixture,
  fetchMe,
  fetchPedagogyGoldenFixture,
  fetchPedagogyGoldenFixtures,
  runPedagogyGoldenSuite,
  savePedagogyGoldenFixture,
  type PedagogyGoldenFixtureSummary,
  type PedagogyGoldenRunResult,
  type User,
} from "@/lib/api";

const EMPTY_JSON = `{
  "summary": "Kurzbeschreibung des Fachs",
  "methods": [
    { "label": "Strategie 1", "when": "Wann anwenden", "example": "Beispiel" },
    { "label": "Strategie 2", "when": "Wann anwenden", "example": "Beispiel" }
  ],
  "exercise_patterns": ["Aufgabentyp"],
  "worked_examples": []
}`;

export default function AdminGoldenSetPage() {
  const [user, setUser] = useState<User | null>(null);
  const [fixtures, setFixtures] = useState<PedagogyGoldenFixtureSummary[]>([]);
  const [runResult, setRunResult] = useState<PedagogyGoldenRunResult | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [editorName, setEditorName] = useState("neues_fixture");
  const [editorJson, setEditorJson] = useState(EMPTY_JSON);
  const [minLabels, setMinLabels] = useState(2);
  const [subjectHint, setSubjectHint] = useState("");
  const [editable, setEditable] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const selectedFixture = useMemo(
    () => fixtures.find((row) => row.name === selected) || null,
    [fixtures, selected],
  );

  async function reload() {
    const res = await fetchPedagogyGoldenFixtures();
    setFixtures(res.fixtures);
  }

  useEffect(() => {
    fetchMe()
      .then((u) => {
        setUser(u);
        if (!u.is_admin) setError("Nur Admins");
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Fehler"));
  }, []);

  useEffect(() => {
    if (!user?.is_admin) return;
    reload().catch((err) => setError(err instanceof Error ? err.message : "Fehler"));
  }, [user?.is_admin]);

  async function onRunSuite() {
    setBusy(true);
    setError(null);
    try {
      const res = await runPedagogyGoldenSuite();
      setRunResult(res);
      setFixtures(res.fixtures);
      setMessage(`Suite: ${res.passed}/${res.total} bestanden`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Suite fehlgeschlagen");
    } finally {
      setBusy(false);
    }
  }

  async function onSelect(name: string) {
    setSelected(name);
    setError(null);
    setMessage(null);
    try {
      const row = await fetchPedagogyGoldenFixture(name);
      setEditorName(row.name);
      setMinLabels(row.min_method_labels);
      setSubjectHint(row.subject_hint || "");
      setEditable(row.editable);
      const content = { ...row.content };
      delete content._meta;
      setEditorJson(JSON.stringify(content, null, 2));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fixture konnte nicht geladen werden");
    }
  }

  function onNew() {
    setSelected(null);
    setEditorName("neues_fixture");
    setEditorJson(EMPTY_JSON);
    setMinLabels(2);
    setSubjectHint("");
    setEditable(true);
    setMessage(null);
    setError(null);
  }

  async function onSave(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const content = JSON.parse(editorJson) as Record<string, unknown>;
      const name = editorName.trim();
      const saved = await savePedagogyGoldenFixture(name, {
        name,
        content,
        min_method_labels: minLabels,
        subject_hint: subjectHint.trim() || null,
      });
      setSelected(saved.name);
      setEditable(true);
      await reload();
      setMessage(`Fixture «${saved.name}» gespeichert und validiert.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Speichern fehlgeschlagen");
    } finally {
      setBusy(false);
    }
  }

  async function onDelete() {
    if (!selected || !editable) return;
    if (!window.confirm(`Fixture «${selected}» wirklich löschen?`)) return;
    setBusy(true);
    setError(null);
    try {
      await deletePedagogyGoldenFixture(selected);
      setMessage(`«${selected}» gelöscht.`);
      onNew();
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Löschen fehlgeschlagen");
    } finally {
      setBusy(false);
    }
  }

  if (error && !user) {
    return (
      <main className="shell">
        <AppHeader />
        <p className="err">{error}</p>
      </main>
    );
  }

  return (
    <main className="shell shell-wide admin-page">
      <AppHeader user={user} title="Golden Set" />
      {error && <p className="err">{error}</p>}
      {message && <p className="muted">{message}</p>}

      <section className="card unit-section">
        <h2>Pedagogy Golden Set</h2>
        <p className="muted section-lead">
          Regressionstests für die Didaktik-Pipeline — repräsentative JSON-Extraktionen (Mathe, Sprache,
          Natur). Vorlage-Fixtures sind schreibgeschützt; eigene Fixtures werden serverseitig gespeichert.
        </p>
        <div className="filter-row">
          <button type="button" className="btn-primary" onClick={onRunSuite} disabled={busy || !user?.is_admin}>
            {busy ? "Läuft…" : "Alle Tests ausführen"}
          </button>
          <button type="button" className="btn" onClick={onNew} disabled={!user?.is_admin}>
            Neues Fixture
          </button>
        </div>
        {runResult && (
          <p className="muted">
            Letzter Lauf: {runResult.passed}/{runResult.total} bestanden
            {runResult.failed > 0 ? ` — ${runResult.failed} fehlgeschlagen` : ""}
          </p>
        )}
      </section>

      <div className="admin-golden-layout">
        <section className="card unit-section">
          <h3>Fixtures ({fixtures.length})</h3>
          <ul className="admin-golden-list">
            {fixtures.map((row) => (
              <li key={row.name}>
                <button
                  type="button"
                  className={`admin-golden-item${selected === row.name ? " active" : ""}`}
                  onClick={() => onSelect(row.name)}
                >
                  <span>
                    <strong>{row.name}</strong>
                    {row.subject_hint ? <span className="muted"> — {row.subject_hint}</span> : null}
                  </span>
                  <span className={`badge ${row.ok ? "badge-ready" : "badge-neutral"}`}>
                    {row.ok ? "OK" : "Fehler"}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </section>

        <section className="card unit-section">
          <h3>{selected ? `Bearbeiten: ${selected}` : "Neues Fixture"}</h3>
          {selectedFixture && !selectedFixture.ok && selectedFixture.error ? (
            <p className="err">{selectedFixture.error}</p>
          ) : null}
          <form className="stack" onSubmit={onSave}>
            <label>
              Name (Dateiname ohne .json)
              <input
                value={editorName}
                onChange={(e) => setEditorName(e.target.value)}
                disabled={!user?.is_admin || (Boolean(selected) && !editable)}
                required
              />
            </label>
            <label>
              Fach-Hinweis (optional)
              <input value={subjectHint} onChange={(e) => setSubjectHint(e.target.value)} disabled={!user?.is_admin} />
            </label>
            <label>
              Mindestanzahl Methoden-Labels
              <input
                type="number"
                min={1}
                max={20}
                value={minLabels}
                onChange={(e) => setMinLabels(Number(e.target.value))}
                disabled={!user?.is_admin}
              />
            </label>
            <label>
              JSON-Inhalt (Vision-Extraktion)
              <textarea
                className="admin-golden-editor"
                rows={18}
                value={editorJson}
                onChange={(e) => setEditorJson(e.target.value)}
                disabled={!user?.is_admin || (Boolean(selected) && !editable)}
                spellCheck={false}
              />
            </label>
            {!editable && selected ? (
              <p className="muted">Vorlage-Fixtures sind schreibgeschützt — «Neues Fixture» oder Kopie anlegen.</p>
            ) : null}
            <div className="filter-row">
              <button type="submit" className="btn-primary" disabled={busy || !user?.is_admin || (Boolean(selected) && !editable)}>
                Speichern & validieren
              </button>
              {selected && editable ? (
                <button type="button" className="btn-sm ghost danger-text" onClick={onDelete} disabled={busy}>
                  Löschen
                </button>
              ) : null}
            </div>
          </form>
        </section>
      </div>

      <p className="muted">
        <Link href="/admin/users">← Benutzer-Verwaltung</Link>
      </p>
    </main>
  );
}
