"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { AppHeader } from "@/components/AppHeader";
import { LearnerMultiSelect } from "@/components/LearnerMultiSelect";
import {
  createUnit,
  fetchMe,
  fetchProfiles,
  fetchUnitTaskTypes,
  isUnitCreateBatch,
  type LearnerProfile,
  type User,
} from "@/lib/api";
import {
  FALLBACK_MATH_FOCUS,
  FALLBACK_TASK_TYPES,
  showMathFocus,
  type MathFocusOption,
  type UnitTaskType,
} from "@/lib/taskTypes";

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
  const [mathFocus, setMathFocus] = useState("");
  const [autoPurge, setAutoPurge] = useState(false);
  const [profileIds, setProfileIds] = useState<string[]>([]);
  const [profiles, setProfiles] = useState<LearnerProfile[]>([]);
  const [taskTypes, setTaskTypes] = useState<UnitTaskType[]>(FALLBACK_TASK_TYPES);
  const [mathFocusOptions, setMathFocusOptions] = useState<MathFocusOption[]>(FALLBACK_MATH_FOCUS);
  const [error, setError] = useState<string | null>(null);

  const selectedType = useMemo(
    () => taskTypes.find((t) => t.key === taskType) ?? taskTypes[0],
    [taskTypes, taskType],
  );

  const mathFocusVisible = showMathFocus(taskType, subject);

  useEffect(() => {
    fetchMe()
      .then((u) => {
        setUser(u);
        if (u.must_enroll_2fa) window.location.href = "/settings";
        if (!u.is_child) {
          fetchProfiles()
            .then((rows) => {
              setProfiles(rows);
              const children = rows.filter((r) => r.is_child_profile);
              if (children.length === 1) {
                setProfileIds([children[0].id]);
              } else if (children.length > 1) {
                setProfileIds(children.map((c) => c.id));
              } else if (rows[0]) {
                setProfileIds([rows[0].id]);
              }
            })
            .catch(() => undefined);
        }
      })
      .catch(() => setError("Nicht angemeldet"));
    fetchUnitTaskTypes()
      .then((data) => {
        if (data.task_types?.length) setTaskTypes(data.task_types);
        if (data.math_focus?.length) setMathFocusOptions(data.math_focus);
      })
      .catch(() => undefined);
  }, []);

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    try {
      const result = await createUnit({
        title: title.trim(),
        brief: brief.trim() || undefined,
        subject: subject.trim() || undefined,
        language,
        target_age: targetAge.trim() || undefined,
        difficulty,
        task_type: taskType,
        math_focus: mathFocusVisible && mathFocus ? mathFocus : undefined,
        auto_purge_sources: autoPurge,
        profile_ids: profileIds.length > 0 ? profileIds : undefined,
      });
      if (isUnitCreateBatch(result)) {
        router.push(`/units/${result.units[0]?.id || ""}`);
      } else {
        router.push(`/units/${result.id}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fehler");
    }
  }

  if (error && !user) {
    return (
      <main className="shell">
        <p>{error}</p>
        <Link href="/login">Zum Login</Link>
      </main>
    );
  }

  return (
    <main className="shell">
      <AppHeader user={user} title="Neue Lerneinheit" />
      <form onSubmit={onCreate} className="card stack">
        <label>
          Titel
          <input
            required
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="z.B. Einstieg ins Bruchrechnen"
          />
        </label>
        <label>
          Beschreibung / Auftrag an die KI
          <textarea
            value={brief}
            onChange={(e) => setBrief(e.target.value)}
            rows={5}
            placeholder="Was soll gelernt werden? Fotos vom Lernmittel kannst du danach hochladen."
          />
        </label>
        <label>
          Fach / Thema
          <input
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            placeholder="Mathematik, Französisch, Grammatik…"
          />
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
          Zielalter
          <input
            value={targetAge}
            onChange={(e) => setTargetAge(e.target.value)}
            placeholder="z.B. 10-14"
          />
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
        {selectedType && (
          <p className="muted" style={{ margin: 0, fontSize: "0.92rem" }}>
            {selectedType.description}
          </p>
        )}
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
            <span className="muted" style={{ fontWeight: 400, fontSize: "0.85rem" }}>
              Kein eigener Modus pro Rechenart — der Schwerpunkt steuert die KI (Bruchrechnen, Geometrie,
              Einheiten …). Details im Auftrag ergänzen.
            </span>
          </label>
        )}
        {!user?.is_child && profiles.length > 0 && (
          <LearnerMultiSelect
            profiles={profiles}
            selectedIds={profileIds}
            onChange={setProfileIds}
            label="Für welche Kinder?"
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
        <label style={{ display: "flex", gap: 8, alignItems: "center", fontWeight: 600 }}>
          <input type="checkbox" checked={autoPurge} onChange={(e) => setAutoPurge(e.target.checked)} />
          Quellenfotos nach OCR/Vision automatisch löschen (Metadaten bleiben)
        </label>
        {error && <p className="err">{error}</p>}
        <button type="submit" className="btn-primary">
          Einheit anlegen
        </button>
      </form>
    </main>
  );
}
