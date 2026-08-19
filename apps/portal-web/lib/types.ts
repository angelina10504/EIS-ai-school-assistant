export type Role = "student" | "parent" | "teacher" | "principal";

export interface User {
  id: string;
  name: string;
  role: Role;
  preferred_language: string;
}

export interface LoginResponse {
  token: string;
  user: User;
  session_id: string;
}

export interface ChatResponse {
  response: string;
  intent: string | null;
  language: string;
  requires_confirmation: boolean;
  permitted: boolean;
  security_flags: string[];
  trace: string[];
  data: Record<string, unknown> | null;
}

export interface TTSMark {
  name: string;
  word: string;
  seconds: number;
}

export interface TTSResponse {
  audio_base64: string;
  mime_type: string;
  language: string;
  marks: TTSMark[];
}

export interface ChatMessage {
  id: string;
  sender: "user" | "assistant";
  text: string;
  intent?: string | null;
  data?: Record<string, unknown> | null;
  flags?: string[];
  pending?: boolean;
}
