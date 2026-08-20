"use client";

import type { Role, User } from "./types";

const KEY = "eis-ai-session";

export interface StoredSession {
  token: string;
  user: User;
  sessionId: string;
}

export function saveSession(session: StoredSession) {
  localStorage.setItem(KEY, JSON.stringify(session));
}

export function loadSession(): StoredSession | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as StoredSession;
  } catch {
    return null;
  }
}

export function clearSession() {
  localStorage.removeItem(KEY);
}

export const rolePath: Record<Role, string> = {
  student: "/student",
  parent: "/parent",
  teacher: "/teacher",
  principal: "/principal",
};
