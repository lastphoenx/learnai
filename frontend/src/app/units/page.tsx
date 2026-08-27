"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { AppHeader } from "@/components/AppHeader";
import { sandboxUnitTitle } from "@/lib/sandboxUnitTitle";
import { fetchMe, fetchUnits, importTrainerJson, type LearningUnit, type User } from "@/lib/api";
import { warmupSpeechInput } from "@/lib/speechWarmup";
import { FALLBACK_TASK_TYPES, languageLabel, taskTypeLabel } from "@/lib/taskTypes";

function statusBadge(status: string) {
  if (status === "ready") return { label: "Bereit", className: "badge badge-ready" };
  if (status === "draft") return { label: "Entwurf", className: "badge badge-draft" };
  return { label: status, className: "badge badge-neutral" };
}

type ProgressFilter = "all" | "not_started" | "in_progress" | "completed" | "no_modules";

export default function UnitsPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [units, setUnits] = useState<LearningUnit[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [taskFilter, setTaskFilter] = useState("all");
  const [learnerFilter, setLearnerFilter] = useState("all");
  const [progressFilter, setProgressFilter] = useState<ProgressFilter>("all");

  useEffect(() => {
    fetchMe()
      .then((u) => {
        setUser(u);
        if (u.must_enroll_2fa) window.location.href = "/settings";
      })
      .catch(() => setError("Nicht angemeldet"));
    fetchUnits()
      .then(setUnits)
      .catch((err) =>
        setError(err instanceof Error ? err.message : "Einheiten konnten nicht geladen werden"),
      );
  }, []);

  const learners = useMemo(() => {
    const names = new Set<string>();
    for (const u of units) {
      if (u.learner_name) names.add(u.learner_name);
    }
    return Array.from(names).sort();
  }, [units]);

  const taskTypes = useMemo(() => {
    const keys = new Set(units.map((u) => u.task_type || "mixed"));
    return Array.from(keys).sort();
  }, [units]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return units.filter((u) => {
      if (q) {
        const hay = [u.title, u.brief, u.subject, u.learner_name, u.target_age]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();
        if (!hay.includes(q)) return false;
      }
      if (statusFilter !== "all" && u.status !== statusFilter) return false;
      if (taskFilter !== "all" && (u.task_type || "mixed") !== taskFilter) return false;
      if (learnerFilter !== "all" && u.learner_name !== learnerFilter) return false;
      if (progressFilter === "no_modules" && u.module_count === 0) return true;
      if (progressFilter === "no_modules") return false;
      const lp = u.learn_progress;
      if (progressFilter === "not_started") {
        return u.module_count > 0 && (!lp || lp.status === "not_started" || lp.percent === 0);
      }
      if (progressFilter === "in_progress") return lp?.status === "in_progress";
      if (progressFilter === "completed") return lp?.status === "completed";
      return true;
    });
  }, [units, query, statusFilter, taskFilter, learnerFilter, progressFilter]);

  function resetFilters() {
    setQuery("");
    setStatusFilter("all");
    setTaskFilter("all");
    setLearnerFilter("all");
    setProgressFilter("all");
  }

  const hasActiveFilters =
    query.trim() !== "" ||
    statusFilter !== "all" ||
    taskFilter !== "all" ||
    learnerFilter !== "all" ||
    progressFilter !== "all";

  if (error && !user) {
    return (
      <main className="shell">
        <p>{error}</p>
        <Link href="/login">Zum Login</Link>
      </main>
    );
  }

  return (
    <main className="shell shell-wide unit-page">
      <AppHeader user={user} title="Lerneinheiten" />
      <section className="card stack">
        <p className="muted" style={{ margin: 0 }}>
          Jede Einheit ist ein eigenes Gefäss: Inhalt und Dateien kannst du später löschen. Verlauf
          und Ergebnisse bleiben.
        </p>
        <p style={{ margin: 0, display: "flex", gap: "0.75rem", flexWrap: "wrap", alignItems: "center" }}>
          <Link
            className="btn btn-primary"
            href="/units/new"
            onClick={() => warmupSpeechInput({ language: "de" })}
          >
            Neue Einheit
          </Link>
          <label className="btn ghost" style={{ cursor: "pointer", margin: 0 }}>
            Trainer importieren (JSON)
            <input
              type="file"
              accept="application/json,.json"
              hidden
              onChange={async (e) => {
                const file = e.target.files?.[0];
                if (!file) return;
                try {
                  const text = await file.text();
                  const payload = JSON.parse(text) as unknown;
                  const unit = await importTrainerJson(payload);
                  window.location.href = `/units/${unit.id}`;
                } catch (err) {
                  setError(err instanceof Error ? err.message : "Import fehlgeschlagen");
                } finally {
                  e.target.value = "";
                }
              }}
            />
          </label>
        </p>
        {error && <p className="err">{error}</p>}
      </section>

      {units.length > 0 && (
        <section className="card filter-bar">
          <div className="filter-row">
            <input
              className="filter-search"
              type="search"
              placeholder="Suchen (Titel, Fach, Beschreibung…)"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              aria-label="Einheiten durchsuchen"
            />
            {hasActiveFilters && (
              <button type="button" className="btn-sm ghost" onClick={resetFilters}>
                Filter zurücksetzen
              </button>
            )}
          </div>
          <div className="filter-row">
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} aria-label="Status">
              <option value="all">Alle Status</option>
              <option value="draft">Entwurf</option>
              <option value="ready">Bereit</option>
            </select>
            <select value={taskFilter} onChange={(e) => setTaskFilter(e.target.value)} aria-label="Aufgabentyp">
              <option value="all">Alle Modi</option>
              {taskTypes.map((key) => (
                <option key={key} value={key}>
                  {taskTypeLabel(key, FALLBACK_TASK_TYPES)}
                </option>
              ))}
            </select>
            {learners.length > 1 && (
              <select value={learnerFilter} onChange={(e) => setLearnerFilter(e.target.value)} aria-label="Lernende">
                <option value="all">Alle Lernenden</option>
                {learners.map((name) => (
                  <option key={name} value={name}>
                    {name}
                  </option>
                ))}
              </select>
            )}
            <select
              value={progressFilter}
              onChange={(e) => setProgressFilter(e.target.value as ProgressFilter)}
              aria-label="Lernfortschritt"
            >
              <option value="all">Alle Fortschritte</option>
              <option value="no_modules">Ohne Blöcke</option>
              <option value="not_started">Noch nicht begonnen</option>
              <option value="in_progress">In Bearbeitung</option>
              <option value="completed">Abgeschlossen</option>
            </select>
          </div>
          <p className="filter-count muted">
            {filtered.length} von {units.length} Einheit{units.length === 1 ? "" : "en"}
          </p>
        </section>
      )}

      <section className="card" style={{ padding: units.length ? "0.75rem" : "1.25rem" }}>
        {units.length === 0 ? (
          <p className="muted" style={{ margin: 0 }}>
            Noch keine Einheiten — starte mit der ersten aus deinen Unterlagen.
          </p>
        ) : filtered.length === 0 ? (
          <p className="muted" style={{ margin: 0 }}>
            Keine Treffer — Filter anpassen oder zurücksetzen.
          </p>
        ) : (
          <ul className="unit-list">
            {filtered.map((u) => {
              const badge = statusBadge(u.status);
              return (
                <li
                  key={u.id}
                  className={`unit-list-item card unit-list-card${u.is_sandbox_copy ? " unit-list-card-sandbox" : ""}`}
                  onClick={(e) => {
                    if ((e.target as HTMLElement).closest("a, button, input, label")) return;
                    router.push(`/units/${u.id}`);
                  }}
                  onKeyDown={(e) => {
                    if (e.key !== "Enter" && e.key !== " ") return;
                    if ((e.target as HTMLElement).closest("a, button")) return;
                    e.preventDefault();
                    router.push(`/units/${u.id}`);
                  }}
                  role="link"
                  tabIndex={0}
                  aria-label={`Einheit öffnen: ${u.title}`}
                >
                  <div className="unit-list-link">
                    <div className="unit-list-head">
                      <span className="unit-list-title">{sandboxUnitTitle(u)}</span>
                      <span className={badge.className}>{badge.label}</span>
                    </div>
                    <div className="badge-row" style={{ marginTop: "0.55rem" }}>
                      {u.reference_code && (
                        <span className="badge badge-neutral unit-ref-badge">Ref {u.reference_code}</span>
                      )}
                      {u.is_sandbox_copy && <span className="badge badge-sandbox">Testkopie</span>}
                      {u.learner_name && <span className="badge badge-neutral">{u.learner_name}</span>}
                      <span className="badge badge-subject">{u.subject || "Ohne Fach"}</span>
                      <span className="badge badge-mode">{taskTypeLabel(u.task_type || "mixed")}</span>
                      <span className="badge badge-neutral">{languageLabel(u.language)}</span>
                      <span className="badge badge-neutral">Stufe {u.difficulty}</span>
                      <span className="badge badge-neutral">{u.source_count} Quellen</span>
                      <span className="badge badge-neutral">{u.module_count} Blöcke</span>
                      {u.learn_progress?.status === "completed" && (
                        <span className="badge badge-ready">Abgeschlossen</span>
                      )}
                      {u.learn_progress?.status === "in_progress" && u.learn_progress.percent > 0 && (
                        <span className="badge badge-neutral">{u.learn_progress.percent}% gelernt</span>
                      )}
                    </div>
                    {u.brief && <p className="unit-list-brief">{u.brief}</p>}
                  </div>
                  {u.module_count > 0 && (
                    <div className="unit-list-actions">
                      <Link
                        className="btn btn-primary"
                        href={`/units/${u.id}/learn`}
                        onClick={(e) => e.stopPropagation()}
                      >
                        {u.learn_progress?.status === "in_progress"
                          ? "Weiterlernen"
                          : u.learn_progress?.status === "completed"
                            ? "Nochmal"
                            : "Lernen"}
                      </Link>
                      <Link className="btn ghost" href={`/units/${u.id}`} onClick={(e) => e.stopPropagation()}>
                        Bearbeiten
                      </Link>
                    </div>
                  )}
                  {u.module_count === 0 && (
                    <p className="muted unit-list-open-hint">Klick irgendwo auf die Karte zum Öffnen</p>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </main>
  );
}
