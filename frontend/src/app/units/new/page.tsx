"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { AppHeader } from "@/components/AppHeader";
import { createUnit, fetchMe, fetchProfiles, type LearnerProfile, type User } from "@/lib/api";

export default function NewUnitPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [title, setTitle] = useState("");
  const [brief, setBrief] = useState("");
  const [subject, setSubject] = useState("");
  const [language, setLanguage] = useState("de");
  const [targetAge, setTargetAge] = useState("");
  const [difficulty, setDifficulty] = useState(1);
  const [taskType, setTaskType] = useState("mixed");
  const [autoPurge, setAutoPurge] = useState(false);
  const [profileId, setProfileId] = useState("");
  const [profiles, setProfiles] = useState<LearnerProfile[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchMe()
      .then((u) => {
        setUser(u);
        if (u.must_enroll_2fa) window.location.href = "/settings";
        if (!u.is_child) {
          fetchProfiles()
            .then((rows) => {
              setProfiles(rows);
              setProfileId(u.profile_id && rows.some((r) => r.id === u.profile_id) ? u.profile_id : rows[0]?.id || "");
            })
            .catch(() => undefined);
        }
      })
      .catch(() => setError("Nicht angemeldet"));
  }, []);

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    try {
      const unit = await createUnit({
        title: title.trim(),
        brief: brief.trim() || undefined,
        subject: subject.trim() || undefined,
        language,
        target_age: targetAge.trim() || undefined,
        difficulty,
        task_type: taskType,
        auto_purge_sources: autoPurge,
        profile_id: profileId || undefined,
      });
      router.push(`/units/${unit.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fehler");
    }
  }

  if (error && !user) {
    return (
      <main style={{ maxWidth: 720, margin: "3rem auto", padding: "0 1.5rem" }}>
        <p>{error}</p>
        <Link href="/login">Zum Login</Link>
      </main>
    );
  }

  return (
    <main style={{ maxWidth: 720, margin: "3rem auto", padding: "0 1.5rem" }}>
      <AppHeader user={user} title="Neue Lerneinheit" />
      <form onSubmit={onCreate} style={{ display: "grid", gap: "0.9rem" }}>
        <label>
          Titel
          <input
            required
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="z.B. Einstieg ins Bruchrechnen"
            style={{ display: "block", width: "100%", marginTop: 4, padding: 8 }}
          />
        </label>
        <label>
          Beschreibung / Auftrag an die KI
          <textarea
            value={brief}
            onChange={(e) => setBrief(e.target.value)}
            rows={5}
            placeholder="Was soll gelernt werden? Fotos vom Lernmittel kannst du danach hochladen."
            style={{ display: "block", width: "100%", marginTop: 4, padding: 8 }}
          />
        </label>
        <label>
          Fach / Thema
          <input
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            placeholder="Mathematik, Französisch, Grammatik…"
            style={{ display: "block", width: "100%", marginTop: 4, padding: 8 }}
          />
        </label>
        <label>
          Sprache
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            style={{ display: "block", width: "100%", marginTop: 4, padding: 8 }}
          >
            <option value="de">Deutsch</option>
            <option value="fr">Französisch</option>
            <option value="it">Italienisch</option>
            <option value="en">Englisch</option>
          </select>
        </label>
        <label>
          Zielalter
          <input
            value={targetAge}
            onChange={(e) => setTargetAge(e.target.value)}
            placeholder="z.B. 6-12"
            style={{ display: "block", width: "100%", marginTop: 4, padding: 8 }}
          />
        </label>
        <label>
          Aufgabentyp
          <select
            value={taskType}
            onChange={(e) => setTaskType(e.target.value)}
            style={{ display: "block", width: "100%", marginTop: 4, padding: 8 }}
          >
            <option value="mixed">Gemischt (Lerntext + Quiz)</option>
            <option value="explain">Erklären / Lerntext</option>
            <option value="quiz">Quiz / Verständnisfragen</option>
            <option value="vocab">Vokabeln / Sprache</option>
            <option value="practice">Übungen</option>
            <option value="exam">Kurzprüfung</option>
          </select>
        </label>
        {profiles.length > 1 && (
          <label>
            Für wen?
            <select
              value={profileId}
              onChange={(e) => setProfileId(e.target.value)}
              style={{ display: "block", width: "100%", marginTop: 4, padding: 8 }}
            >
              {profiles.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.display_name}
                  {p.is_child_profile ? " (Kind)" : ""}
                </option>
              ))}
            </select>
          </label>
        )}
        <label>
          Schwierigkeit (1–5)
          <input
            type="number"
            min={1}
            max={5}
            value={difficulty}
            onChange={(e) => setDifficulty(Number(e.target.value))}
            style={{ display: "block", width: "100%", marginTop: 4, padding: 8 }}
          />
        </label>
        <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <input
            type="checkbox"
            checked={autoPurge}
            onChange={(e) => setAutoPurge(e.target.checked)}
          />
          Quellenfotos nach OCR/Vision automatisch löschen (Metadaten bleiben)
        </label>
        {error && <p style={{ color: "#ef4444" }}>{error}</p>}
        <button type="submit">Einheit anlegen</button>
      </form>
    </main>
  );
}
