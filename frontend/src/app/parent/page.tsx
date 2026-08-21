"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { AppHeader } from "@/components/AppHeader";
import { TransferComparison } from "@/components/TransferComparison";
import {
  childReportUrl,
  childReportPdfUrl,
  createReviewUnit,
  reviewUnitHref,
  fetchMe,
  fetchParentDashboard,
  fetchParentExamInsights,
  type ChildDashboardStats,
  type ChildExamInsights,
  type User,
} from "@/lib/api";

function formatDate(iso: string) {
  try {
    return new Date(iso).toLocaleDateString("de-CH");
  } catch {
    return iso.slice(0, 10);
  }
}

export default function ParentDashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [children, setChildren] = useState<ChildDashboardStats[]>([]);
  const [insights, setInsights] = useState<ChildExamInsights[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchMe()
      .then((u) => {
        setUser(u);
        if (u.is_child) {
          setError("Nur für Eltern-Accounts");
          return;
        }
        return Promise.all([fetchParentDashboard(), fetchParentExamInsights()]).then(([d, ins]) => {
          setChildren(d.children);
          setInsights(ins.children);
        });
      })
      .catch((e: Error) => setError(e.message));
  }, []);

  if (error && !user) {
    return (
      <main className="shell">
        <p>{error}</p>
        <Link href="/login">Zum Login</Link>
      </main>
    );
  }

  return (
    <main className="shell shell-wide">
      <AppHeader user={user} title="Kinder-Übersicht" />
      <p className="muted">
        Lernfortschritt, Prüfungstrends, Wiederholungs-Erinnerungen und Berichte für Elterngespräche.
      </p>
      {error && <p className="err">{error}</p>}

      {children.length === 0 ? (
        <p className="muted">
          Noch keine Kinder verknüpft. Unter{" "}
          <Link href="/settings">Einstellungen</Link> oder Admin → Benutzer kannst du Kind-Accounts anlegen.
        </p>
      ) : (
        <div className="stack">
          {children.map((child) => {
            const exam = insights.find((i) => i.user_id === child.user_id);
            return (
              <section key={child.user_id} className="card stack parent-child-card">
                <div className="section-head">
                  <h2 style={{ margin: 0 }}>{child.display_name}</h2>
                  {exam?.profile_id && (
                    <>
                      <a className="btn btn-sm ghost" href={childReportPdfUrl(exam.profile_id)}>
                        Bericht (PDF)
                      </a>
                      <a className="btn btn-sm ghost" href={childReportUrl(exam.profile_id)}>
                        Bericht (Markdown)
                      </a>
                    </>
                  )}
                </div>
                <p className="muted" style={{ margin: 0 }}>
                  {child.active_units} aktive Einheit{child.active_units !== 1 ? "en" : ""} · {child.completed}{" "}
                  abgeschlossen · {child.in_progress} in Bearbeitung
                  {child.quiz_total > 0
                    ? ` · Quiz ${child.quiz_correct}/${child.quiz_total} (${child.quiz_percent}%)`
                    : ""}
                  {child.flashcard_total > 0
                    ? ` · ${child.flashcard_known}/${child.flashcard_total} Karten sicher`
                    : ""}
                  {exam && exam.exam_count > 0 ? ` · ${exam.exam_count} Schulprüfung(en)` : ""}
                </p>

                {(child.trainer_units || []).length > 0 && (
                  <div className="parent-insight-block">
                    <h3>Lerntrainer</h3>
                    <ul className="list parent-trainer-list">
                      {(child.trainer_units || []).map((tu) => {
                        const pct = tu.card_count
                          ? Math.round((100 * tu.known_cards) / tu.card_count)
                          : 0;
                        return (
                          <li key={tu.unit_id} className="card parent-trainer-item">
                            <div className="parent-trainer-head">
                              <strong>{tu.title}</strong>
                              <span className="muted">
                                {tu.known_cards}/{tu.card_count} Karten sicher ({pct}%)
                                {(tu.due_cards ?? 0) > 0 ? ` · ${tu.due_cards} fällig` : ""}
                              </span>
                            </div>
                            <div className="trainer-progress-bar" aria-hidden="true">
                              <div className="trainer-progress-fill" style={{ width: `${pct}%` }} />
                            </div>
                            {tu.review_cards > 0 && (
                              <p className="muted" style={{ margin: "0.35rem 0 0", fontSize: "0.85rem" }}>
                                {tu.review_cards} zum Wiederholen markiert
                              </p>
                            )}
                            <p style={{ margin: "0.5rem 0 0", display: "flex", gap: 8, flexWrap: "wrap" }}>
                              <Link className="btn btn-sm btn-primary" href={`/units/${tu.unit_id}/learn`}>
                                Trainer öffnen
                              </Link>
                              <Link className="btn btn-sm" href={`/units/${tu.unit_id}`}>
                                Einheit
                              </Link>
                            </p>
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                )}

                {exam && exam.review_due.length > 0 && (
                  <div className="parent-insight-block">
                    <h3>Wiederholung empfohlen</h3>
                    <p className="muted section-lead">
                      Abgeschlossene Einheiten vor mehr als 7 Tagen — kurze Wiederholung festigt das Gelernte.
                    </p>
                    <ul className="list">
                      {exam.review_due.map((r) => (
                        <li key={r.record_id} className="card" style={{ boxShadow: "none", padding: "0.75rem" }}>
                          <strong>{r.title}</strong>
                          <span className="muted" style={{ marginLeft: 8, fontSize: "0.85rem" }}>
                            vor {r.days_since} Tagen abgeschlossen
                          </span>
                          <p style={{ margin: "0.5rem 0 0", display: "flex", gap: 8, flexWrap: "wrap" }}>
                            {r.unit_id && (
                              <>
                                <button
                                  type="button"
                                  className="btn btn-sm btn-primary"
                                  onClick={async () => {
                                    try {
                                      const unit = await createReviewUnit(r.unit_id!);
                                      router.push(reviewUnitHref(unit));
                                    } catch (e) {
                                      alert(e instanceof Error ? e.message : "Wiederholung fehlgeschlagen");
                                    }
                                  }}
                                >
                                  Wiederholung erstellen
                                </button>
                                <Link className="btn btn-sm" href={`/units/${r.unit_id}`}>
                                  Einheit
                                </Link>
                              </>
                            )}
                          </p>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {exam && exam.pending_remediation > 0 && (
                  <p className="parent-alert muted">
                    {exam.pending_remediation} analysierte Prüfung{exam.pending_remediation !== 1 ? "en" : ""} ohne
                    Nacharbeit — auf der Einheitsseite «Nacharbeit erstellen» wählen.
                  </p>
                )}

                {exam && exam.error_tags.length > 0 && (
                  <div className="parent-insight-block">
                    <h3>Fehlertrends (über alle Prüfungen)</h3>
                    <ul className="exam-pattern-list">
                      {exam.error_tags.map((t) => (
                        <li key={t.tag}>
                          <span className="badge badge-math">{t.label}</span>
                          <span className="muted">
                            {" "}
                            · {t.count}× · in {t.exam_count} Prüfung{t.exam_count !== 1 ? "en" : ""}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {exam && exam.timeline.length > 0 && (
                  <div className="parent-insight-block">
                    <h3>Prüfungsverlauf</h3>
                    <ul className="list">
                      {exam.timeline.map((row) => (
                        <li key={row.exam_id} className="card" style={{ boxShadow: "none", padding: "0.75rem" }}>
                          <strong>{row.unit_title || "Ohne Einheit"}</strong>
                          <span className="muted" style={{ marginLeft: 8, fontSize: "0.85rem" }}>
                            {formatDate(row.taken_at)} · {row.grade_label || "—"}
                            {row.has_analysis ? " · analysiert" : ""}
                          </span>
                          {row.transfer && (
                            <div style={{ marginTop: "0.5rem" }}>
                              <TransferComparison transfer={row.transfer} compact />
                            </div>
                          )}
                          {row.unit_id && (
                            <p style={{ margin: "0.5rem 0 0" }}>
                              <Link className="btn btn-sm" href={`/units/${row.unit_id}`}>
                                Zur Einheit
                              </Link>
                              {row.remediation_unit_id && (
                                <Link
                                  className="btn btn-sm ghost"
                                  href={`/units/${row.remediation_unit_id}`}
                                  style={{ marginLeft: 8 }}
                                >
                                  Nacharbeit
                                </Link>
                              )}
                            </p>
                          )}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {child.recent.length > 0 && (
                  <div className="parent-insight-block">
                    <h3>Letzte Aktivität</h3>
                    <ul className="list" style={{ margin: 0 }}>
                      {child.recent.map((r) => (
                        <li key={r.record_id} className="card" style={{ boxShadow: "none", padding: "0.75rem" }}>
                          <strong>{r.title}</strong>
                          <span className="muted" style={{ marginLeft: 8, fontSize: "0.85rem" }}>
                            {r.status === "completed"
                              ? "abgeschlossen"
                              : r.status === "in_progress"
                                ? "in Bearbeitung"
                                : "nicht gestartet"}
                            {r.quiz_total > 0 ? ` · Quiz ${r.quiz_correct}/${r.quiz_total}` : ""}
                          </span>
                          <p style={{ margin: "0.5rem 0 0", display: "flex", gap: 8, flexWrap: "wrap" }}>
                            {r.unit_id && (
                              <>
                                <Link className="btn btn-primary" href={`/units/${r.unit_id}/learn`}>
                                  {r.status === "in_progress" ? "Weiterlernen" : "Lernen"}
                                </Link>
                                <Link className="btn" href={`/units/${r.unit_id}`}>
                                  Einheit
                                </Link>
                              </>
                            )}
                          </p>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </section>
            );
          })}
        </div>
      )}
    </main>
  );
}
