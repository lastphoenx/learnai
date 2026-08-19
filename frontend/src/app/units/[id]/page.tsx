"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ChangeEvent, useEffect, useState } from "react";
import { AppHeader } from "@/components/AppHeader";
import {
  deleteSource,
  deleteUnit,
  fetchMe,
  fetchUnit,
  patchUnit,
  purgeSource,
  speak,
  uploadSource,
  type LearningUnit,
  type User,
} from "@/lib/api";

export default function UnitDetailPage() {
  const params = useParams();
  const router = useRouter();
  const unitId = params.id as string;
  const [user, setUser] = useState<User | null>(null);
  const [unit, setUnit] = useState<LearningUnit | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function reload() {
    fetchUnit(unitId).then(setUnit).catch(() => setError("Einheit nicht gefunden"));
  }

  useEffect(() => {
    fetchMe()
      .then((u) => {
        setUser(u);
        if (u.must_enroll_2fa) window.location.href = "/settings";
      })
      .catch(() => setError("Nicht angemeldet"));
  }, []);

  useEffect(() => {
    if (unitId) reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [unitId]);

  async function onFiles(e: ChangeEvent<HTMLInputElement>) {
    const files = e.target.files;
    if (!files?.length) return;
    setBusy(true);
    try {
      for (const file of Array.from(files)) {
        await uploadSource(unitId, file);
      }
      reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload fehlgeschlagen");
    } finally {
      setBusy(false);
      e.target.value = "";
    }
  }

  async function onDeleteUnit() {
    if (
      !confirm(
        "Lerneinheit inkl. Dateien löschen? Verlauf, Ergebnisse und die Kurzbeschreibung bleiben für Berichte und für «ähnlich nochmal» erhalten."
      )
    ) {
      return;
    }
    await deleteUnit(unitId);
    router.push("/history");
  }

  async function onSpeak() {
    if (!unit?.title) return;
    try {
      const blob = await speak(`${unit.title}. ${unit.brief || ""}`, unit.language);
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audio.play();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Vorlesen nicht möglich");
    }
  }

  if (error && !unit) {
    return (
      <main style={{ maxWidth: 720, margin: "3rem auto", padding: "0 1.5rem" }}>
        <p>{error}</p>
        <Link href="/units">Zurück</Link>
      </main>
    );
  }

  return (
    <main style={{ maxWidth: 800, margin: "3rem auto", padding: "0 1.5rem" }}>
      <AppHeader user={user} title={unit?.title ?? "…"} />
      {error && <p style={{ color: "#ef4444" }}>{error}</p>}
      {unit && (
        <>
          <p style={{ color: "var(--muted)" }}>
            {unit.subject || "ohne Fach"} · {unit.language} · Stufe {unit.difficulty}
            {unit.target_age ? ` · ${unit.target_age}` : ""}
          </p>
          {unit.brief && <p>{unit.brief}</p>}
          <p style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button type="button" onClick={onSpeak}>
              Vorlesen (OpenAI TTS)
            </button>
            <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <input
                type="checkbox"
                checked={unit.auto_purge_sources}
                onChange={async (e) => {
                  const next = await patchUnit(unit.id, e.target.checked);
                  setUnit(next);
                }}
              />
              Fotos nach OCR automatisch löschen
            </label>
          </p>

          <h2 style={{ fontSize: "1.1rem" }}>Quellen (Lernmittel-Fotos / Dokumente)</h2>
          <input type="file" multiple accept="image/*,.pdf,audio/*" onChange={onFiles} disabled={busy} />
          <ul style={{ listStyle: "none", padding: 0 }}>
            {(unit.sources || []).map((s) => (
              <li
                key={s.id}
                style={{
                  border: "1px solid var(--border)",
                  borderRadius: 8,
                  padding: "0.75rem",
                  marginTop: 8,
                  display: "flex",
                  justifyContent: "space-between",
                  gap: 8,
                }}
              >
                <span>
                  {s.original_name || s.kind} · {s.kind}
                  {s.has_file ? "" : " · Datei entfernt"}
                  {s.has_extracted_text ? " · Text vorhanden" : ""}
                </span>
                <span style={{ display: "flex", gap: 8 }}>
                  {s.has_file && (
                    <button type="button" onClick={() => purgeSource(unit.id, s.id).then(reload)}>
                      Nur Datei löschen
                    </button>
                  )}
                  <button type="button" onClick={() => deleteSource(unit.id, s.id).then(reload)}>
                    Quelle weg
                  </button>
                </span>
              </li>
            ))}
          </ul>
          {(unit.modules || []).length > 0 && (
            <>
              <h2 style={{ fontSize: "1.1rem" }}>Lernblöcke</h2>
              <p style={{ color: "var(--muted)" }}>KI-Aufbereitung folgt im nächsten Slice.</p>
            </>
          )}
          <hr style={{ margin: "2rem 0", borderColor: "var(--border)" }} />
          <button type="button" onClick={onDeleteUnit}>
            Ganze Einheit löschen (Verlauf bleibt)
          </button>
        </>
      )}
    </main>
  );
}
