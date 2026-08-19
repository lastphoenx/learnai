const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

type FetchOptions = RequestInit & { json?: unknown };

async function apiFetch<T>(path: string, options: FetchOptions = {}): Promise<T> {
  const { json, headers, ...rest } = options;
  const res = await fetch(`${API_URL}${path}`, {
    ...rest,
    credentials: "include",
    headers: {
      ...(json ? { "Content-Type": "application/json" } : {}),
      ...headers,
    },
    body: json ? JSON.stringify(json) : rest.body,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(typeof err.detail === "string" ? err.detail : `API ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export type HealthResponse = { status: string; tenant: string };
export type User = {
  id: string;
  is_admin: boolean;
  totp_enabled: boolean;
  totp_required: boolean;
  must_enroll_2fa: boolean;
  display_name?: string;
  llm_provider?: string;
  llm_model?: string;
};
export type LoginResponse = { requires_2fa: boolean; must_enroll_2fa?: boolean; user?: User };
export type AdminUser = User & { is_active: boolean; created_at: string };

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
  status: string;
  auto_purge_sources: boolean;
  created_at: string;
  updated_at: string;
  source_count: number;
  module_count: number;
  sources?: UnitSource[];
  modules?: UnitModule[];
};

export type LearningRecord = {
  id: string;
  unit_id: string | null;
  unit_alive: boolean;
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

export const updateMySettings = (body: {
  display_name?: string;
  llm_provider?: string;
  llm_model?: string;
}) => apiFetch<User>("/api/v1/auth/me", { method: "PATCH", json: body });

export const fetchUnits = () => apiFetch<LearningUnit[]>("/api/v1/units");
export const fetchUnit = (id: string) => apiFetch<LearningUnit>(`/api/v1/units/${id}`);
export const createUnit = (body: {
  title: string;
  brief?: string;
  subject?: string;
  language?: string;
  target_age?: string;
  difficulty?: number;
  task_type?: string;
  auto_purge_sources?: boolean;
}) => apiFetch<LearningUnit>("/api/v1/units", { method: "POST", json: body });
export const patchUnit = (id: string, auto_purge_sources: boolean) =>
  apiFetch<LearningUnit>(`/api/v1/units/${id}`, { method: "PATCH", json: { auto_purge_sources } });
export const deleteUnit = (id: string) =>
  apiFetch<void>(`/api/v1/units/${id}`, { method: "DELETE" });

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

export const generateUnit = (unitId: string, provider?: string) =>
  apiFetch<LearningUnit>(`/api/v1/units/${unitId}/generate`, {
    method: "POST",
    json: { provider: provider ?? null },
  });

export const fetchAiStatus = () =>
  apiFetch<{
    llm_provider: string;
    openai: { configured: boolean };
    anthropic: { configured: boolean };
    ollama: { ok?: boolean; url: string; models?: string[]; error?: string };
    tts: { provider: string; configured: boolean };
  }>("/api/v1/ai/status");

export const fetchRecords = () => apiFetch<LearningRecord[]>("/api/v1/records");
export const rebuildFromRecord = (recordId: string, difficulty?: number) =>
  apiFetch<LearningUnit>(`/api/v1/records/${recordId}/rebuild`, {
    method: "POST",
    json: { difficulty: difficulty ?? null },
  });

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
