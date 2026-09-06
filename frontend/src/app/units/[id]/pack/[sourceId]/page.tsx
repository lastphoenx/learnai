"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { AppHeader } from "@/components/AppHeader";
import { HtmlPackFrame, isHtmlSource } from "@/components/HtmlPackFrame";
import { fetchMe, fetchUnit, type LearningUnit, type User } from "@/lib/api";

export default function UnitHtmlPackPage() {
  const params = useParams();
  const unitId = params.id as string;
  const sourceId = params.sourceId as string;
  const [user, setUser] = useState<User | null>(null);
  const [unit, setUnit] = useState<LearningUnit | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchMe()
      .then(setUser)
      .catch(() => setError("Nicht angemeldet"));
    fetchUnit(unitId)
      .then(setUnit)
      .catch((err: Error) => setError(err.message));
  }, [unitId]);

  const source = (unit?.sources || []).find((s) => s.id === sourceId);
  const ready = Boolean(source && source.has_file && isHtmlSource(source));

  return (
    <div className="page html-pack-page">
      <AppHeader user={user} />
      <main className="html-pack-main">
        <div className="html-pack-toolbar">
          <Link className="btn-sm ghost" href={`/units/${unitId}`}>
            ← Zurück zur Einheit
          </Link>
          {source ? <strong>{source.original_name || "HTML-Übung"}</strong> : null}
          {unit?.modules && unit.modules.length > 0 ? (
            <Link className="btn-sm" href={`/units/${unitId}/learn`}>
              Zum Lerntrainer
            </Link>
          ) : null}
        </div>
        {error ? <p className="error">{error}</p> : null}
        {!error && !unit ? <p className="muted">Lade…</p> : null}
        {unit && !ready ? (
          <p className="error">HTML-Übung nicht gefunden oder Datei fehlt.</p>
        ) : null}
        {ready && source ? (
          <HtmlPackFrame unitId={unitId} source={source} className="html-pack-frame html-pack-frame-full" />
        ) : null}
      </main>
    </div>
  );
}
