const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

type FetchOptions = RequestInit & { json?: unknown };

function apiDetailMessage(detail: unknown, status: number): string {
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const parts = detail.map((item) => {
      if (typeof item === "string") return item;
      if (item && typeof item === "object" && "msg" in item) {
        const rec = item as { msg?: unknown; loc?: unknown };
        const loc = Array.isArray(rec.loc)
          ? rec.loc.filter((part) => part !== "body" && part !== "query").join(".")
          : "";
        const msg = String(rec.msg || "");
        return loc ? `${loc}: ${msg}` : msg;
      }
      return "";
    }).filter(Boolean);
    if (parts.length) return parts.join(" · ");
  }
  if (detail && typeof detail === "object" && "message" in detail) {
    return String((detail as { message: unknown }).message);
  }
  return `API ${status}`;
}

async function apiFetch<T>(path: string, options: FetchOptions = {}): Promise<T> {
  const { json, headers, ...rest } = options;
  const res = await fetch(`${API_URL}${path}`, {
    ...rest,
    cache: "no-store",
    credentials: "include",
    headers: {
      ...(json ? { "Content-Type": "application/json" } : {}),
      ...headers,
    },
    body: json ? JSON.stringify(json) : rest.body,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(apiDetailMessage(err.detail ?? err, res.status));
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export type HealthResponse = { status: string; tenant: string };
export type User = {
  id: string;
  is_admin: boolean;
  is_child?: boolean;
  parent_id?: string | null;
  parent_ids?: string[];
  profile_id?: string | null;
  learner_name?: string;
  child_count?: number;
  totp_enabled: boolean;
  totp_required: boolean;
  must_enroll_2fa: boolean;
  display_name?: string;
  login_email?: string;
  llm_provider?: string;
  llm_model?: string;
  by_task?: Record<string, { provider: string; model: string }>;
  ki_summary?: string;
};
export type LoginResponse = { requires_2fa: boolean; must_enroll_2fa?: boolean; user?: User };
export type AdminUser = User & { is_active: boolean; created_at: string };

export type LearnerProfile = {
  id: string;
  display_name: string;
  user_id: string | null;
  managed_by_id: string;
  is_child_profile: boolean;
  llm_provider: string;
  llm_model: string;
  by_task: Record<string, { provider: string; model: string }>;
  stt_provider: string;
  default_language: string;
  target_age: string;
  auto_purge_sources: boolean;
  created_at: string;
};

export type SttProvider = "browser" | "local" | "openai" | "anthropic";

export type SttStatus = {
  browser: { configured: boolean };
  local: { configured: boolean };
  openai: { configured: boolean };
  anthropic: { configured: boolean };
};

export type AiModelCatalog = {
  openai: {
    ok: boolean;
    configured: boolean;
    chat: string[];
    vision: string[];
    tts: string[];
    error?: string | null;
  };
  anthropic: {
    ok: boolean;
    configured: boolean;
    chat: string[];
    vision: string[];
    error?: string | null;
  };
};

export type UnitSource = {
  id: string;
  kind: string;
  original_name: string | null;
  content_type: string | null;
  byte_size: number;
  has_file: boolean;
  has_extracted_text: boolean;
  purged_at: string | null;
  created_at: string;
};

export type LearnProgress = {
  status: "not_started" | "in_progress" | "completed";
  module_index: number;
  phase: "intro" | "read" | "practice" | "quiz" | "module_done" | "complete";
  question_index: number;
  modules: Record<
    string,
    {
      text_read?: boolean;
      answers?: (number | null)[];
      answer_details?: Record<
        string,
        {
          selected: number;
          correct: boolean;
          correct_index: number;
          explanation?: string;
          attempts?: number;
          first_attempt_correct?: boolean;
          retry_available_at?: string | null;
        }
      >;
      deferred?: number[];
      practice_answers?: ({ answer: string; correct: boolean } | null)[];
      correct?: number;
      total?: number;
      done?: boolean;
    }
  >;
  quiz_correct: number;
  quiz_total: number;
  started_at: string | null;
  completed_at: string | null;
};

export type LearnSummary = {
  status: string;
  modules_done: number;
  module_count: number;
  percent: number;
  quiz_correct: number;
  quiz_total: number;
};

export type LearnModule = {
  id: string;
  order_index: number;
  title: string;
  content: { text?: string; practice?: PracticeItem[] } | null;
  quiz: { questions?: { q: string; options?: string[] }[] } | null;
};

export type PracticeItem = {
  prompt: string;
  hint?: string | null;
  answer_type?: "text" | "number" | string;
};

export type CardKindGoal = number | "all" | null;

export type LearnGoals = {
  quiz?: number | null;
  cards?: {
    merk?: CardKindGoal;
    mental?: CardKindGoal;
    input?: CardKindGoal;
  };
  deadline?: string | null;
};

export type GoalProgressItem = {
  key: string;
  label: string;
  done: number;
  target: number | null;
  percent: number | null;
  met: boolean | null;
  bonus: number;
  remaining: number | null;
  message: string | null;
};

export type GoalsProgressBlock = {
  source: string;
  quiz?: number | null;
  cards?: LearnGoals["cards"];
  deadline?: string | null;
  days_left?: number | null;
  overdue?: boolean;
  items: GoalProgressItem[];
  met_count: number;
  active_count: number;
  overall_percent: number | null;
  headline: string | null;
};

export type GoalsProgress = {
  parent: GoalsProgressBlock;
  child: GoalsProgressBlock;
  quiz_done: number;
  card_done: Record<string, number>;
  card_available: Record<string, number>;
};

export type TrainerOptions = {
  cards: number;
  questions: number;
  style: "balanced" | "playful" | "factual";
  answer_length: "short" | "medium" | "long";
  llm_provider?: string | null;
};

export type TrainerKnowledgeItem = {
  title: string;
  text: string;
  domain?: string;
  module_id?: string;
};

export type TrainerKnowledgeSection = {
  domain: string;
  module_id: string;
  intro?: string;
  items: { title: string; text: string }[];
};

export type TrainerContentAnalysis = {
  overview: string;
  quiz: {
    total: number;
    summary: string;
    methods_summary?: string;
    operations: { key: string; label: string; count: number; percent: number }[];
    methods?: { key: string; label: string; count: number; percent: number }[];
  };
  cards: {
    total: number;
    summary: string;
    methods_summary?: string;
    operations: { key: string; label: string; count: number; percent: number }[];
    methods?: { key: string; label: string; count: number; percent: number }[];
  };
  by_module: {
    domain: string;
    quiz_total: number;
    card_total: number;
    quiz_ops: { key: string; label: string; count: number; percent: number }[];
    card_ops: { key: string; label: string; count: number; percent: number }[];
    quiz_methods?: { key: string; label: string; count: number; percent: number }[];
    card_methods?: { key: string; label: string; count: number; percent: number }[];
  }[];
};

export type UnitPedagogy = {
  has_pedagogy: boolean;
  digest: string;
  source_count: number;
  refreshed_sources?: number;
  can_reread?: number;
  skipped_no_file?: number;
  analysis_current?: boolean;
  analysis_version?: number;
  image_count?: number;
  last_extract?: {
    status: "success" | "partial" | "failed" | "stale" | string;
    updated_at: string;
    message?: string;
    refreshed_sources?: number;
    skipped_no_file?: number;
  };
  quality?: {
    level: "good" | "partial" | "low" | string;
    method_count: number;
    methods_with_when?: number;
    worked_with_steps: number;
    pattern_count: number;
  };
  profile: {
    methods?: { id?: string; label: string; when?: string; example?: string }[];
    worked_examples?: {
      problem: string;
      steps?: string[];
      method_id?: string;
      method_label?: string;
    }[];
    exercise_patterns?: string[];
    teaching_notes?: string[];
  };
  sources: {
    id: string;
    kind: string;
    original_name: string | null;
    has_pedagogy: boolean;
    analysis_current?: boolean;
    method_count: number;
    exercise_count: number;
  }[];
};

export const METHOD_LABELS: Record<string, string> = {
  mental: "Im Kopf",
  notes: "Mit Notizen",
  numberline: "Rechenstrich",
  written: "Schriftlich",
  decomposition: "Zerlegung",
  supplement: "Ergänzen",
  method_choice: "Strategiewahl",
  other: "Sonstiges",
};

export type TrainerPayload = {
  options: TrainerOptions;
  knowledge: TrainerKnowledgeItem[];
  knowledge_sections?: TrainerKnowledgeSection[];
  content_analysis?: TrainerContentAnalysis;
  cards: {
    question: string;
    answer: string;
    tip?: string;
    kind?: "merk" | "mental" | "input" | string;
    expected_method?: string;
    method_id?: string;
    domain?: string;
    module_id: string;
    card_index: number;
    card_key: string;
  }[];
  flashcard_progress: Record<string, {
    status: string;
    attempts: number;
    last_seen_at?: string | null;
    next_review_at?: string | null;
    interval_days?: number;
    due?: boolean;
  }>;
  stats: {
    card_count: number;
    question_count: number;
    known_cards: number;
    review_cards: number;
    due_cards: number;
    new_cards?: number;
    merk_cards?: number;
    mental_cards?: number;
    input_cards?: number;
  };
  learn_goals?: LearnGoals;
  child_goals?: LearnGoals;
  goals_progress?: GoalsProgress;
};

export type LearnState = {
  unit: LearningUnit;
  record_id: string;
  modules: LearnModule[];
  progress: LearnProgress;
  summary: LearnSummary;
  trainer?: TrainerPayload;
  quiz_weaknesses?: QuizWeaknesses;
  exam_entry?: ExamLearnEntry | null;
};

export type QuizWeaknessItem = {
  module_id: string;
  module_title: string;
  question_index: number;
  question: string;
  selected: number;
  selected_label?: string | null;
  correct_index: number;
  correct_label?: string | null;
  explanation?: string | null;
  error_tags?: string[];
};

export type QuizErrorTagRow = {
  key?: string;
  tag: string;
  label: string;
  count: number;
};

export type ExamLearnEntry = {
  exam_id: string;
  source_unit_id?: string | null;
  source_unit_title?: string | null;
  taken_at?: string | null;
  summary?: string | null;
  gaps?: string[];
  error_tags?: { key?: string; tag: string; label: string }[];
  remediation_unit_id?: string | null;
  trainer_unit_id?: string | null;
  match?: "same_unit" | "same_subject";
};

export type QuizWeaknesses = {
  quiz_correct: number;
  quiz_total: number;
  wrong_count: number;
  weaknesses: QuizWeaknessItem[];
  error_tags?: QuizErrorTagRow[];
  remediation_unit_id?: string | null;
  trainer_unit_id?: string | null;
  can_remediate: boolean;
};

export type UnitModule = {
  id: string;
  order_index: number;
  title: string;
  content: unknown;
  quiz: unknown;
};

export type LearningUnit = {
  id: string;
  title: string;
  brief: string | null;
  subject: string | null;
  language: string;
  target_age: string | null;
  difficulty: number;
  task_type?: string;
  math_focus?: string | null;
  status: string;
  auto_purge_sources: boolean;
  created_at: string;
  updated_at: string;
  source_count: number;
  module_count: number;
  learn_progress?: LearnSummary;
  profile_id?: string | null;
  learner_name?: string | null;
  template_unit_id?: string | null;
  template_root_id?: string | null;
  is_sandbox_copy?: boolean;
  sandbox_copy_of?: string | null;
  reference_family?: string | null;
  reference_instance?: string | null;
  reference_code?: string | null;
  trainer_options?: TrainerOptions;
  learn_goals?: LearnGoals;
  sources?: UnitSource[];
  modules?: UnitModule[];
  exams?: ExamResult[];
  last_generate?: GenerateJobStatus | null;
};

export type ExamTransfer = {
  quiz_correct: number;
  quiz_total: number;
  quiz_percent: number | null;
  exam_score: number | null;
  exam_max_score: number | null;
  exam_percent: number | null;
  gap_percent: number | null;
  signal:
    | "transfer_gap"
    | "exam_better"
    | "aligned"
    | "quiz_only"
    | "exam_only"
    | "insufficient_data";
};

export type ExamResult = {
  id: string;
  unit_id: string | null;
  record_id: string;
  taken_at: string | null;
  exam_type: string;
  grade_label: string | null;
  score: number | null;
  max_score: number | null;
  notes: string | null;
  original_name: string | null;
  content_type: string | null;
  byte_size: number;
  has_file: boolean;
  status: string;
  analysis?: ExamAnalysis | null;
  analysis_edited?: boolean;
  transfer?: ExamTransfer | null;
  remediation_unit_id?: string | null;
  trainer_unit_id?: string | null;
  created_at: string;
  updated_at: string;
};

export type ExamAnalysis = {
  summary?: string;
  strengths?: string[];
  gaps?: string[];
  error_patterns?: {
    tag?: string;
    label?: string;
    count?: number;
    examples?: string[];
  }[];
  tasks?: {
    index?: number;
    description?: string;
    correct?: boolean;
    points_earned?: number;
    max_points?: number;
    errors?: string[];
    error_tags?: string[];
  }[];
  recommendations?: string[];
  provider?: string;
  model?: string;
};

export type ExamAnalysisPatchBody = {
  summary?: string | null;
  strengths?: string[] | null;
  gaps?: string[] | null;
  error_patterns?: ExamAnalysis["error_patterns"] | null;
  tasks?: ExamAnalysis["tasks"] | null;
  recommendations?: string[] | null;
};

export type ExamPatchBody = {
  taken_at?: string | null;
  exam_type?: string;
  grade_label?: string | null;
  score?: number | null;
  max_score?: number | null;
  notes?: string | null;
};

export type ExamUploadMeta = {
  taken_at?: string;
  exam_type?: string;
  grade_label?: string;
  score?: number;
  max_score?: number;
  notes?: string;
};

export type LearningRecord = {
  id: string;
  unit_id: string | null;
  unit_alive: boolean;
  profile_id?: string | null;
  learner_name?: string | null;
  title: string;
  summary: string | null;
  subject: string | null;
  language: string;
  difficulty: number;
  reconstruction: {
    title?: string;
    brief?: string;
    subject?: string | null;
    language?: string;
    target_age?: string | null;
    difficulty?: number;
  } | null;
  stats: Record<string, unknown>;
  last_activity_at: string;
  created_at: string;
  exam_count?: number;
  events?: { id: string; event_type: string; payload: unknown; created_at: string }[];
};

export const fetchHealth = () => apiFetch<HealthResponse>("/api/v1/health");
export const fetchMe = () => apiFetch<User>("/api/v1/auth/me");
export const login = (email: string, password: string) =>
  apiFetch<LoginResponse>("/api/v1/auth/login", { method: "POST", json: { email, password } });
export const verify2fa = (totp_code?: string, recovery_code?: string) =>
  apiFetch<LoginResponse>("/api/v1/auth/2fa/verify", {
    method: "POST",
    json: { totp_code, recovery_code },
  });
export const logout = () => apiFetch<void>("/api/v1/auth/logout", { method: "POST" });
export const setup2fa = (email: string) =>
  apiFetch<{ provisioning_uri: string; secret: string }>("/api/v1/auth/2fa/setup", {
    method: "POST",
    json: { email },
  });
export const confirm2fa = (code: string, email: string) =>
  apiFetch<{ recovery_codes: string[] }>("/api/v1/auth/2fa/confirm", {
    method: "POST",
    json: { code, email },
  });

export const fetchUsers = () => apiFetch<AdminUser[]>("/api/v1/users");
export const setTotpPolicy = (userId: string, totp_required: boolean) =>
  apiFetch<User>(`/api/v1/users/${userId}/totp-policy`, {
    method: "PATCH",
    json: { totp_required },
  });

export const createUser = (body: {
  email: string;
  password: string;
  display_name?: string;
  is_admin?: boolean;
  totp_required?: boolean;
}) => apiFetch<AdminUser>("/api/v1/users", { method: "POST", json: body });

export const updateAdminUser = (
  userId: string,
  body: { display_name?: string; login_email?: string },
) => apiFetch<AdminUser>(`/api/v1/users/${userId}`, { method: "PATCH", json: body });

export const resetAdminUserPassword = (
  userId: string,
  body: { new_password: string; email?: string },
) =>
  apiFetch<void>(`/api/v1/users/${userId}/password`, { method: "POST", json: body });

export const createChildUser = (body: {
  email: string;
  password: string;
  display_name: string;
  parent_id?: string;
  parent_ids?: string[];
}) => apiFetch<AdminUser>("/api/v1/users/children", { method: "POST", json: body });

export const updateChildGuardians = (userId: string, parent_ids: string[]) =>
  apiFetch<AdminUser>(`/api/v1/users/${userId}/guardians`, {
    method: "PATCH",
    json: { parent_ids },
  });

export type PedagogyGoldenFixtureSummary = {
  name: string;
  file?: string;
  ok: boolean;
  min_method_labels?: number;
  subject_group?: string | null;
  subject_group_label?: string | null;
  subject_hint?: string | null;
  method_count?: number;
  label_count?: number;
  pattern_count?: number;
  digest_preview?: string;
  summary?: string | null;
  error?: string;
};

export type PedagogyGoldenCoverage = {
  expected_groups: { id: string; label: string }[];
  covered: { id: string; label: string; fixtures: string[] }[];
  missing: { id: string; label: string }[];
  complete: boolean;
};

export type PedagogyGoldenStatus = {
  fixtures: PedagogyGoldenFixtureSummary[];
  coverage: PedagogyGoldenCoverage;
  total: number;
  passed: number;
  failed: number;
  coverage_complete: boolean;
  ok: boolean;
  report: string;
};

export const fetchPedagogyGoldenStatus = () =>
  apiFetch<PedagogyGoldenStatus>("/api/v1/admin/pedagogy-golden");

export const runPedagogyGoldenSuite = () =>
  apiFetch<PedagogyGoldenStatus>("/api/v1/admin/pedagogy-golden/run", { method: "POST" });

export type UnitQualityReport = {
  ref: string;
  scope: "family" | "instance";
  family: string;
  instance: string | null;
  unit_count: number;
  report: string;
  ok: boolean;
};

export const fetchUnitQualityReport = (ref: string) =>
  apiFetch<UnitQualityReport>(`/api/v1/admin/unit-report?ref=${encodeURIComponent(ref)}`);

export const updateMySettings = (body: { display_name?: string }) =>
  apiFetch<User>("/api/v1/auth/me", { method: "PATCH", json: body });

export const changeMyPassword = (body: { current_password: string; new_password: string }) =>
  apiFetch<void>("/api/v1/auth/me/password", { method: "POST", json: body });

export const fetchProfiles = () => apiFetch<LearnerProfile[]>("/api/v1/profiles");
export const fetchProfile = (id: string) => apiFetch<LearnerProfile>(`/api/v1/profiles/${id}`);
export const updateProfile = (
  id: string,
  body: {
    display_name?: string;
    llm_provider?: string;
    llm_model?: string;
    by_task?: Record<string, { provider: string; model: string }>;
    default_language?: string;
    target_age?: string;
    auto_purge_sources?: boolean;
    stt_provider?: SttProvider;
  },
) => apiFetch<LearnerProfile>(`/api/v1/profiles/${id}`, { method: "PATCH", json: body });
export const applyProfileRecommendations = (id: string) =>
  apiFetch<LearnerProfile>(`/api/v1/profiles/${id}/apply-recommendations`, { method: "POST" });

export const fetchUnits = () => apiFetch<LearningUnit[]>("/api/v1/units");

export type UnitTaskTypesResponse = {
  task_types: { key: string; label: string; select_label?: string; description: string; hint: string }[];
  math_focus: { key: string; label: string }[];
  focus_groups: { id: string; label: string; options: { key: string; label: string }[] }[];
};

export const fetchUnitTaskTypes = () => apiFetch<UnitTaskTypesResponse>("/api/v1/units/task-types");
export const fetchUnit = (id: string) => apiFetch<LearningUnit>(`/api/v1/units/${id}`);
export const fetchUnitPedagogy = (id: string) => apiFetch<UnitPedagogy>(`/api/v1/units/${id}/pedagogy`);
export const extractUnitPedagogy = (id: string) =>
  apiFetch<UnitPedagogy>(`/api/v1/units/${id}/pedagogy/extract`, { method: "POST" });
export type UnitCreateBody = {
  title: string;
  brief?: string;
  subject?: string;
  language?: string;
  target_age?: string;
  difficulty?: number;
  task_type?: string;
  math_focus?: string;
  auto_purge_sources?: boolean;
  profile_id?: string;
  profile_ids?: string[];
};

export type UnitCreateBatchResult = { units: LearningUnit[]; created_count: number };

export function isUnitCreateBatch(
  res: LearningUnit | UnitCreateBatchResult,
): res is UnitCreateBatchResult {
  return typeof res === "object" && res !== null && "created_count" in res;
}

export const createUnit = (body: UnitCreateBody) =>
  apiFetch<LearningUnit | UnitCreateBatchResult>("/api/v1/units", { method: "POST", json: body });

export const patchUnitProfile = (unitId: string, profileId: string | null) =>
  apiFetch<LearningUnit>(`/api/v1/units/${unitId}/profile`, {
    method: "PATCH",
    json: { profile_id: profileId },
  });

export const assignUnitToProfiles = (unitId: string, profileIds: string[]) =>
  apiFetch<UnitCreateBatchResult>(`/api/v1/units/${unitId}/assign`, {
    method: "POST",
    json: { profile_ids: profileIds },
  });

export const createTestCopyUnit = (unitId: string) =>
  apiFetch<LearningUnit>(`/api/v1/units/${unitId}/test-copy`, { method: "POST" });
export type UnitPatchBody = {
  title?: string;
  brief?: string | null;
  subject?: string | null;
  language?: string;
  target_age?: string | null;
  difficulty?: number;
  task_type?: string;
  math_focus?: string | null;
  auto_purge_sources?: boolean;
  trainer_options?: Partial<TrainerOptions>;
  learn_goals?: LearnGoals | null;
};

export const patchUnit = (id: string, body: UnitPatchBody) =>
  apiFetch<LearningUnit>(`/api/v1/units/${id}`, { method: "PATCH", json: body });
export const deleteUnit = (id: string, opts?: { purgeHistory?: boolean }) => {
  const q = opts?.purgeHistory ? "?purge_history=true" : "";
  return apiFetch<void>(`/api/v1/units/${id}${q}`, { method: "DELETE" });
};

export async function uploadSource(unitId: string, file: File): Promise<UnitSource> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_URL}/api/v1/units/${unitId}/sources`, {
    method: "POST",
    credentials: "include",
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(typeof err.detail === "string" ? err.detail : `API ${res.status}`);
  }
  return res.json();
}

export const deleteSource = (unitId: string, sourceId: string) =>
  apiFetch<void>(`/api/v1/units/${unitId}/sources/${sourceId}`, { method: "DELETE" });
export const purgeSource = (unitId: string, sourceId: string) =>
  apiFetch<UnitSource>(`/api/v1/units/${unitId}/sources/${sourceId}/purge`, { method: "POST" });

export function sourceFileUrl(unitId: string, sourceId: string) {
  return `${API_URL}/api/v1/units/${unitId}/sources/${sourceId}/file`;
}

export async function uploadExam(unitId: string, file: File, meta: ExamUploadMeta): Promise<ExamResult> {
  const form = new FormData();
  form.append("file", file);
  if (meta.taken_at) form.append("taken_at", meta.taken_at);
  if (meta.exam_type) form.append("exam_type", meta.exam_type);
  if (meta.grade_label) form.append("grade_label", meta.grade_label);
  if (meta.score != null) form.append("score", String(meta.score));
  if (meta.max_score != null) form.append("max_score", String(meta.max_score));
  if (meta.notes) form.append("notes", meta.notes);
  const res = await fetch(`${API_URL}/api/v1/units/${unitId}/exams`, {
    method: "POST",
    credentials: "include",
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(typeof err.detail === "string" ? err.detail : `API ${res.status}`);
  }
  return res.json();
}

export const patchExam = (unitId: string, examId: string, body: ExamPatchBody) =>
  apiFetch<ExamResult>(`/api/v1/units/${unitId}/exams/${examId}`, { method: "PATCH", json: body });

export const patchExamAnalysis = (unitId: string, examId: string, body: ExamAnalysisPatchBody) =>
  apiFetch<ExamResult>(`/api/v1/units/${unitId}/exams/${examId}/analysis`, { method: "PATCH", json: body });

export const deleteExam = (unitId: string, examId: string) =>
  apiFetch<void>(`/api/v1/units/${unitId}/exams/${examId}`, { method: "DELETE" });

export const fetchRecordExams = (recordId: string) =>
  apiFetch<ExamResult[]>(`/api/v1/records/${recordId}/exams`);

export function examFileUrl(unitId: string, examId: string) {
  return `${API_URL}/api/v1/units/${unitId}/exams/${examId}/file`;
}

export const analyzeExam = (unitId: string, examId: string) =>
  apiFetch<ExamResult>(`/api/v1/units/${unitId}/exams/${examId}/analyze`, { method: "POST" });

export type RemediationResponse = { exam: ExamResult; unit: LearningUnit };

export const createRemediationFromExam = (unitId: string, examId: string) =>
  apiFetch<RemediationResponse>(`/api/v1/units/${unitId}/exams/${examId}/remediation`, {
    method: "POST",
  });

export const createInteractiveTrainerFromExam = (unitId: string, examId: string) =>
  apiFetch<RemediationResponse>(`/api/v1/units/${unitId}/exams/${examId}/interactive-trainer`, {
    method: "POST",
  });

export type GenerateJobStatus = {
  status: "idle" | "queued" | "running" | "done" | "partial" | "failed";
  stage?: string | null;
  message?: string | null;
  progress_pct?: number | null;
  error?: string | null;
  started_at?: string | null;
  updated_at?: string | null;
  modules?: number | null;
  cards?: number | null;
  questions?: number | null;
};

export type GenerateStartResponse = {
  async_job: boolean;
  job: GenerateJobStatus;
};

export type GenerateStatusResponse = {
  job: GenerateJobStatus;
  unit?: LearningUnit | null;
};

export type GenerateUnitResult =
  | { mode: "sync"; unit: LearningUnit }
  | { mode: "async"; job: GenerateJobStatus };

export async function generateUnit(
  unitId: string,
  provider?: string,
  opts?: { force?: boolean },
): Promise<GenerateUnitResult> {
  const res = await fetch(`${API_URL}/api/v1/units/${unitId}/generate`, {
    method: "POST",
    credentials: "include",
    cache: "no-store",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ provider: provider ?? null, force: Boolean(opts?.force) }),
  });
  const body = await res.json().catch(() => ({}));
  if (res.status === 202) {
    const payload = body as GenerateStartResponse;
    return { mode: "async", job: payload.job };
  }
  if (!res.ok) {
    const detail = typeof body.detail === "string" ? body.detail : `API ${res.status}`;
    throw new Error(detail);
  }
  return { mode: "sync", unit: body as LearningUnit };
}

export const fetchGenerateStatus = (unitId: string) =>
  apiFetch<GenerateStatusResponse>(`/api/v1/units/${unitId}/generate/status`);

export async function cancelGenerate(unitId: string): Promise<GenerateJobStatus> {
  const res = await apiFetch<GenerateStatusResponse>(`/api/v1/units/${unitId}/generate/cancel`, {
    method: "POST",
  });
  return res.job;
}

export async function waitForGenerateJob(
  unitId: string,
  onUpdate?: (job: GenerateJobStatus) => void,
  intervalMs = 3000,
): Promise<LearningUnit> {
  for (;;) {
    const res = await fetchGenerateStatus(unitId);
    onUpdate?.(res.job);
    if (res.job.status === "done" || res.job.status === "partial") {
      if (res.unit) return res.unit;
      return fetchUnit(unitId);
    }
    if (res.job.status === "failed") {
      throw new Error(res.job.error || res.job.message || "KI-Aufbereitung fehlgeschlagen");
    }
    if (res.job.status === "idle") {
      throw new Error("Kein laufender Generierungsjob");
    }
    await new Promise((r) => setTimeout(r, intervalMs));
  }
}

export const fetchLearnState = (unitId: string) =>
  apiFetch<LearnState>(`/api/v1/units/${unitId}/learn`);

export const patchChildLearnGoals = (unitId: string, body: LearnGoals) =>
  apiFetch<{ child_goals: LearnGoals; goals_progress: GoalsProgress }>(
    `/api/v1/units/${unitId}/learn/child-goals`,
    { method: "PATCH", json: body },
  );

export const saveLearnPosition = (
  unitId: string,
  body: { module_index: number; phase: LearnProgress["phase"]; question_index?: number },
) =>
  apiFetch<{ progress: LearnProgress; summary: LearnSummary }>(
    `/api/v1/units/${unitId}/learn/position`,
    { method: "PATCH", json: body },
  );

export const markLearnTextRead = (unitId: string, moduleId: string) =>
  apiFetch<{ progress: LearnProgress; summary: LearnSummary }>(
    `/api/v1/units/${unitId}/learn/text-read`,
    { method: "POST", json: { module_id: moduleId } },
  );

export const submitLearnAnswer = (
  unitId: string,
  body: { module_id: string; question_index: number; selected: number },
) =>
  apiFetch<{
    correct: boolean;
    correct_index: number;
    explanation?: string;
    attempt_number?: number;
    retry_available_at?: string | null;
    progress: LearnProgress;
    summary: LearnSummary;
    module_quiz_done: boolean;
    quiz_weaknesses?: QuizWeaknesses;
    auto_trainer_unit_id?: string | null;
    auto_trainer_started?: boolean;
  }>(`/api/v1/units/${unitId}/learn/answer`, { method: "POST", json: body });

export const deferLearnQuestion = (
  unitId: string,
  body: { module_id: string; question_index: number },
) =>
  apiFetch<{ progress: LearnProgress; summary: LearnSummary }>(
    `/api/v1/units/${unitId}/learn/defer`,
    { method: "POST", json: body },
  );

export const submitPracticeAnswer = (
  unitId: string,
  body: { module_id: string; exercise_index: number; answer: string },
) =>
  apiFetch<{
    correct: boolean;
    hint?: string | null;
    expected?: string | null;
    progress: LearnProgress;
    summary: LearnSummary;
    practice_done: boolean;
  }>(`/api/v1/units/${unitId}/learn/practice`, { method: "POST", json: body });

export const submitCardInputAnswer = (
  unitId: string,
  body: { module_id: string; card_index: number; answer: string; worked_solution?: string },
) =>
  apiFetch<{
    correct: boolean;
    result_correct: boolean;
    worked_correct?: boolean | null;
    worked_feedback?: string | null;
    explanation?: string | null;
    expected?: string | null;
    progress: LearnProgress;
    summary: LearnSummary;
    card_key: string;
    flashcard_progress?: TrainerPayload["flashcard_progress"];
  }>(`/api/v1/units/${unitId}/learn/card-input`, { method: "POST", json: body });

export const markFlashcardStatus = (
  unitId: string,
  body: { module_id: string; card_index: number; status: "known" | "review" | "unseen" },
) =>
  apiFetch<{
    flashcard_progress: TrainerPayload["flashcard_progress"];
    card_key: string;
    status: string;
  }>(`/api/v1/units/${unitId}/learn/flashcard`, { method: "POST", json: body });

export const completeLearn = (unitId: string) =>
  apiFetch<{
    progress: LearnProgress;
    summary: LearnSummary;
    quiz_weaknesses?: QuizWeaknesses;
    auto_trainer_unit_id?: string | null;
    auto_trainer_started?: boolean;
  }>(`/api/v1/units/${unitId}/learn/complete`, { method: "POST" });

export const resetLearnProgress = (unitId: string) =>
  apiFetch<{ progress: LearnProgress; summary: LearnSummary }>(
    `/api/v1/units/${unitId}/learn/reset`,
    { method: "POST" },
  );

export const fetchQuizWeaknesses = (unitId: string) =>
  apiFetch<QuizWeaknesses>(`/api/v1/units/${unitId}/learn/weaknesses`);

export type QuizRemediationResponse = { weaknesses: QuizWeaknesses; unit: LearningUnit };

export const createRemediationFromQuiz = (unitId: string) =>
  apiFetch<QuizRemediationResponse>(`/api/v1/units/${unitId}/learn/remediation`, { method: "POST" });

export const createInteractiveTrainerFromQuiz = (unitId: string) =>
  apiFetch<QuizRemediationResponse>(`/api/v1/units/${unitId}/learn/interactive-trainer`, {
    method: "POST",
  });

export type ChildDashboardStats = {
  user_id: string;
  display_name: string;
  profile_id: string | null;
  active_units: number;
  records_total: number;
  completed: number;
  in_progress: number;
  quiz_correct: number;
  quiz_total: number;
  quiz_percent: number | null;
  flashcard_known: number;
  flashcard_total: number;
  trainer_units: {
    unit_id: string;
    title: string;
    status: string;
    known_cards: number;
    review_cards: number;
    due_cards: number;
    card_count: number;
  }[];
  recent: {
    record_id: string;
    unit_id: string | null;
    title: string;
    status: string;
    quiz_correct: number;
    quiz_total: number;
    last_activity_at: string;
  }[];
};

export const fetchParentDashboard = () =>
  apiFetch<{ children: ChildDashboardStats[]; child_count: number }>("/api/v1/dashboard/parent");

export type ChildExamInsights = {
  user_id: string;
  profile_id: string;
  display_name: string;
  exam_count: number;
  analyzed_count: number;
  pending_remediation: number;
  timeline: {
    exam_id: string;
    unit_id: string | null;
    unit_title: string | null;
    taken_at: string;
    grade_label: string | null;
    score: number | null;
    max_score: number | null;
    has_analysis: boolean;
    status: string;
    remediation_unit_id: string | null;
    transfer?: ExamTransfer | null;
  }[];
  error_tags: { key: string; tag: string; label: string; count: number; exam_count: number }[];
  strategy_trends?: {
    key: string;
    label: string;
    attempts: number;
    correct: number;
    accuracy: number | null;
    unit_count: number;
    sources: string[];
  }[];
  review_due: {
    record_id: string;
    unit_id: string | null;
    title: string;
    completed_at: string;
    days_since: number;
  }[];
};

export const fetchParentExamInsights = () =>
  apiFetch<{ children: ChildExamInsights[] }>("/api/v1/dashboard/parent/exam-insights");

export function childReportUrl(profileId: string) {
  return `${API_URL}/api/v1/dashboard/parent/report/${profileId}`;
}

export function childReportPdfUrl(profileId: string) {
  return `${API_URL}/api/v1/dashboard/parent/report/${profileId}/pdf`;
}

export function unitWorksheetPdfUrl(unitId: string) {
  return `${API_URL}/api/v1/units/${unitId}/worksheet.pdf`;
}

export function unitTrainerExportUrl(unitId: string) {
  return `${API_URL}/api/v1/units/${unitId}/export/trainer.json`;
}

export const importTrainerJson = (payload: unknown) =>
  apiFetch<LearningUnit>("/api/v1/units/import/trainer", { method: "POST", json: payload });

export const addSourceUrl = (unitId: string, url: string) =>
  apiFetch<UnitSource>(`/api/v1/units/${unitId}/sources/url`, {
    method: "POST",
    json: { url },
  });

export type TaskCatalogItem = {
  key: string;
  label: string;
  why: string;
  default_provider: string;
  local: string[];
  external: string[];
  /** Bis zu 3 installierte Ollama-Modelle (vom Server aufgelöst) */
  local_resolved?: string[];
  /** Bis zu 3 verfügbare Cloud-Modelle (vom Server aufgelöst) */
  external_resolved?: string[];
};

export const fetchAiStatus = () =>
  apiFetch<{
    llm_provider: string;
    openai: { configured: boolean };
    anthropic: { configured: boolean };
    ollama: { ok?: boolean; configured?: boolean; url: string; models?: string[]; error?: string };
    tts: { provider: string; configured: boolean };
    stt?: SttStatus;
    task_catalog?: TaskCatalogItem[];
    models?: AiModelCatalog;
  }>("/api/v1/ai/status");

export async function transcribeSpeech(
  blob: Blob,
  language: string,
  profileId?: string,
): Promise<{ text: string; provider: string }> {
  const form = new FormData();
  form.append("file", blob, "recording.webm");
  form.append("language", language);
  if (profileId) form.append("profile_id", profileId);
  const res = await fetch(`${API_URL}/api/v1/ai/transcribe`, {
    method: "POST",
    credentials: "include",
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(apiDetailMessage(err.detail ?? err, res.status));
  }
  return res.json();
}

export const warmupStt = (profileId?: string) => {
  const q = profileId ? `?profile_id=${encodeURIComponent(profileId)}` : "";
  return apiFetch<{ ok: boolean; provider: string; error?: string }>(`/api/v1/ai/stt/warmup${q}`, {
    method: "POST",
  });
};

export const fetchRecords = () => apiFetch<LearningRecord[]>("/api/v1/records");
export const rebuildFromRecord = (recordId: string, difficulty?: number, task_type?: string) =>
  apiFetch<LearningUnit>(`/api/v1/records/${recordId}/rebuild`, {
    method: "POST",
    json: { difficulty: difficulty ?? null, task_type: task_type ?? null },
  });

export const createReviewUnit = (unitId: string) =>
  apiFetch<LearningUnit & { review_mode?: string }>(`/api/v1/units/${unitId}/review`, { method: "POST" });

export function reviewUnitHref(unit: { id: string; review_mode?: string; task_type?: string | null }) {
  if (unit.review_mode === "quiz_trainer" || unit.task_type === "interactive") {
    return `/units/${unit.id}/learn?autogen=1`;
  }
  return `/units/${unit.id}?autogen=1`;
}

export async function speak(text: string, lang = "de"): Promise<Blob> {
  const res = await fetch(`${API_URL}/api/v1/ai/tts`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, lang }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(typeof err.detail === "string" ? err.detail : "TTS fehlgeschlagen");
  }
  return res.blob();
}
