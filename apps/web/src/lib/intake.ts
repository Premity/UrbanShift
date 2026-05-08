const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export type InputType = "text" | "chips" | "multi" | "slider" | "range" | "date";

export interface TurnPrompt {
  en: string;
  hi: string;
  kn: string;
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
