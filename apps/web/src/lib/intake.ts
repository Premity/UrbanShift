const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export type InputType = "text" | "chips" | "multi" | "slider" | "range" | "date";

// Full profile payload — mirrors ProfileSchema (PRD §5.4) + ProfileUpsertRequest
export interface ProfilePayload {
  seeker_type: "job" | "housing" | "both";
  name?: string;
  age: number;
  gender: "male" | "female" | "other" | "prefer_not";
  origin_state: string;
  current_city: "Bengaluru";
  native_lang: string;
  languages_spoken: string[];
  migrant_status: "just_moved" | "planning" | "long_term";
  aadhaar_available: boolean;
  // work
  sector?: string;
  skills: string[];
  education: "none" | "primary" | "class10" | "class12" | "diploma" | "grad" | "postgrad";
  years_experience: number;
  employment_status: "unemployed" | "employed" | "underemployed" | "student";
  income_range_inr?: [number, number] | null;
  worker_band: number;
  // housing
  budget_inr?: number | null;
  preferred_areas: string[];
  occupancy_pref?: "single" | "shared" | "dorm" | "any" | null;
  move_in_window_days?: number | null;
}

export interface TurnPrompt {
  en: string;
  hi: string;
  kn: string;
  [lang: string]: string;  // allow dynamic language lookup
}

export interface Turn {
  field: string;
  prompt_i18n: TurnPrompt;
  input_type: InputType;
  options: string[];
  allow_free_text: boolean;
  multi_select: boolean;
}

export interface TurnResponse {
  complete: boolean;
  turn?: Turn;
  current_profile: Record<string, unknown>;
}

export interface FinalizeResponse {
  session_id: string;
  profile: Record<string, unknown>;
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export async function startSession(langPref: string = "en") {
  return post<{ session_id: string }>("/api/session/start", { lang_pref: langPref });
}

export async function sendTurn(answer?: { field: string; value: unknown }): Promise<TurnResponse> {
  return post<TurnResponse>("/api/intake/turn", answer ? { answer } : {});
}

export async function finalize(): Promise<FinalizeResponse> {
  return post<FinalizeResponse>("/api/intake/finalize");
}

export async function saveProfile(payload: ProfilePayload): Promise<{ session_id: string; seeker_type: string }> {
  return post("/api/profile", {
    seeker_type: payload.seeker_type,
    profile_json: payload,
  });
}

export interface ResumeParseResponse {
  profile: Partial<ProfilePayload>;
  missing_fields: string[];
  parsed_ok: boolean;
}

export async function parseResume(file: File): Promise<ResumeParseResponse> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/api/resume/parse`, {
    method: "POST",
    credentials: "include",
    body: form,
    // Note: do NOT set Content-Type — browser sets it with the boundary automatically
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json() as Promise<ResumeParseResponse>;
}
