"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { AppHeader } from "@/components/AppHeader";
import { LabelWithSpeech } from "@/components/LabelWithSpeech";
import { LearnerMultiSelect } from "@/components/LearnerMultiSelect";
import { UnitFieldGuide } from "@/components/UnitFieldGuide";
import { useChildPreview } from "@/lib/childPreview";
import {
  createUnit,
  fetchMe,
  fetchProfile,
  fetchProfiles,
  fetchUnitTaskTypes,
  isUnitCreateBatch,
  type LearnerProfile,
  type SttProvider,
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
import { FALLBACK_TASK_TYPES, type UnitTaskType } from "@/lib/taskTypes";
import { getUnitFieldGuide } from "@/lib/unitFieldHints";

export default function NewUnitPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const { asChild } = useChildPreview(user);
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
  const [focusGroups, setFocusGroups] = useState<FocusGroup[]>(FALLBACK_FOCUS_GROUPS);
  const [error, setError] = useState<string | null>(null);
  const [sttProvider, setSttProvider] = useState<SttProvider>("browser");
  const [speechProfileId, setSpeechProfileId] = useState<string | undefined>(undefined);

  const activeSpeechProfile = useMemo(() => {
    const id = profileIds[0];
    return profiles.find((p) => p.id === id);
  }, [profileIds, profiles]);

  const selectedType = useMemo(
    () => taskTypes.find((t) => t.key === taskType) ?? taskTypes[0],
    [taskTypes, taskType],
  );

  const mathFocusVisible = showSubjectFocus(taskType, subject);
  const focusGroupId = detectFocusGroup(subject, taskType);
  const focusOptions = focusOptionsForGroup(focusGroupId, focusGroups);
  const focusGroupName = focusGroupLabel(focusGroupId, focusGroups);

  const fieldCtx = useMemo(
    () => ({ taskType, mathFocus, subject }),
    [taskType, mathFocus, subject],
  );

  const titleGuide = useMemo(() => getUnitFieldGuide("title", fieldCtx), [fieldCtx]);
  const briefGuide = useMemo(() => getUnitFieldGuide("brief", fieldCtx), [fieldCtx]);
  const subjectGuide = useMemo(() => getUnitFieldGuide("subject", fieldCtx), [fieldCtx]);
  const targetAgeGuide = useMemo(() => getUnitFieldGuide("targetAge", fieldCtx), [fieldCtx]);

  useEffect(() => {
    if (activeSpeechProfile) {
      setSttProvider((activeSpeechProfile.stt_provider as SttProvider) || "browser");
      setSpeechProfileId(activeSpeechProfile.id);
    }
  }, [activeSpeechProfile]);

  useEffect(() => {
    fetchMe()
      .then((u) => {
        setUser(u);
        if (u.must_enroll_2fa) window.location.href = "/settings";
        if (u.is_child && u.profile_id) {
          fetchProfile(u.profile_id)
            .then((p) => {
              setSttProvider((p.stt_provider as SttProvider) || "browser");
              setSpeechProfileId(p.id);
            })
            .catch(() => undefined);
        } else if (!u.is_child) {
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
        if (data.focus_groups?.length) setFocusGroups(data.focus_groups);
        else if (data.math_focus?.length) {
          setFocusGroups([{ id: "math", label: "Mathematik", options: data.math_focus.filter((o) => o.key) }]);
        }
      })
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!mathFocus) return;
    const valid = focusOptions.some((o) => o.key === mathFocus);
    if (!valid && focusGroupId) setMathFocus("");
  }, [focusGroupId, focusOptions, mathFocus]);

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
        <LabelWithSpeech
          label="Titel"
          language={language}
          sttProvider={sttProvider}
          profileId={speechProfileId}
          onError={(msg) => setError(msg)}
          onTranscript={(text, final) => {
            if (final) {
              setTitle((prev) => `${prev}${prev && !prev.endsWith(" ") ? " " : ""}${text.trim()}`);
            }
          }}
        >
          <>
            <input
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder={titleGuide.placeholder}
            />
            <UnitFieldGuide tip={titleGuide.tip} show={!title.trim()} />
          </>
        </LabelWithSpeech>

        <label>
          Aufgabentyp
          <select value={taskType} onChange={(e) => setTaskType(e.target.value)}>
            {taskTypes.map((t) => (
              <option key={t.key} value={t.key}>
                {t.select_label || t.label}
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
            Schwerpunkt{focusGroupName ? ` — ${focusGroupName}` : ""}
            <select value={mathFocus} onChange={(e) => setMathFocus(e.target.value)}>
              <option value="">— Schwerpunkt (optional) —</option>
              {focusGroupId ? (
                focusOptions.map((o) => (
                  <option key={o.key} value={o.key}>
                    {o.label}
                  </option>
                ))
              ) : (
                focusGroups.map((group) => (
                  <optgroup key={group.id} label={group.label}>
                    {group.options.map((o) => (
                      <option key={o.key} value={o.key}>
                        {o.label}
                      </option>
                    ))}
                  </optgroup>
                ))
              )}
            </select>
            <UnitFieldGuide
              tip={
                focusGroupId
                  ? "Steuert die Vorlagen unten — Details und Ausnahmen im Auftrag formulieren."
                  : "Tipp: Fach eingeben (z.B. Französisch, MGU) — dann passende Schwerpunkte."
              }
              show={!mathFocus}
            />
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

        <LabelWithSpeech
          label="Beschreibung / Auftrag an die KI"
          language={language}
          continuous
          sttProvider={sttProvider}
          profileId={speechProfileId}
          onError={(msg) => setError(msg)}
          onTranscript={(text, final) => {
            if (final) {
              setBrief((prev) => `${prev}${prev && !prev.endsWith(" ") ? " " : ""}${text.trim()}`);
            }
          }}
        >
          <>
            <textarea
              value={brief}
              onChange={(e) => setBrief(e.target.value)}
              rows={8}
              placeholder={briefGuide.placeholder}
            />
            <UnitFieldGuide tip={briefGuide.tip} show={!brief.trim()} />
          </>
        </LabelWithSpeech>

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
        {!asChild && profiles.length > 0 && (
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
