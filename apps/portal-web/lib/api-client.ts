import type { ChatResponse, LoginResponse, TTSResponse, User } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}, token?: string): Promise<T> {
  const headers = new Headers(init.headers);
  if (!(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let response: Response;
  try {
    response = await fetch(`${BASE}${path}`, { ...init, headers });
  } catch {
    throw new ApiError("Can't reach XYZ AI. Is the backend running on port 8000?", 0);
  }

  if (!response.ok) {
    let detail = response.statusText;
    try {
      detail = (await response.json())?.detail ?? detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(typeof detail === "string" ? detail : "Request failed", response.status);
  }
  return (await response.json()) as T;
}

export const api = {
  login: (email: string, password: string) =>
    request<LoginResponse>("/api/session/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  me: (token: string) => request<User>("/api/session/me", {}, token),

  newConversation: (token: string) =>
    request<{ session_id: string; language: string }>("/api/session/new", { method: "POST" }, token),

  setLanguage: (token: string, language: string) =>
    request<User>("/api/session/language", { method: "POST", body: JSON.stringify({ language }) }, token),

  chat: (token: string, sessionId: string, message: string) =>
    request<ChatResponse>(
      "/api/chat",
      { method: "POST", body: JSON.stringify({ session_id: sessionId, message }) },
      token,
    ),

  confirm: (token: string, sessionId: string, confirm: boolean) =>
    request<ChatResponse>(
      "/api/chat/confirm",
      { method: "POST", body: JSON.stringify({ session_id: sessionId, confirm }) },
      token,
    ),

  tts: (token: string, text: string, language: string) =>
    request<TTSResponse>("/api/voice/tts", { method: "POST", body: JSON.stringify({ text, language }) }, token),

  stt: async (token: string, blob: Blob, language: string) => {
    const form = new FormData();
    form.append("audio", blob, "utterance.webm");
    form.append("language", language);
    return request<{ transcript: string; language: string; confidence: number }>(
      "/api/voice/stt",
      { method: "POST", body: form },
      token,
    );
  },

  audit: (token: string) =>
    request<{ entries: { action: string; resource: string; allowed: boolean; at: string }[] }>(
      "/api/audit/recent",
      {},
      token,
    ),
};
