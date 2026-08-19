import matrix from "./permissions.json";

export type Role = "student" | "parent" | "teacher" | "principal";
export type Intent =
  | "view_attendance"
  | "mark_attendance"
  | "view_analytics"
  | "escalate"
  | "general_chat";
export type Scope = "self" | "linked_child" | "own_class" | "school" | "any" | "none";

export const PERMISSION_MATRIX = matrix.matrix as Record<Role, Record<Intent, Scope>>;
export const SUPPORTED_LANGUAGES = matrix.languages as string[];

/**
 * Advisory only. The frontend uses this to hide controls a role cannot use; the
 * decision that matters is made server-side in app/auth/permissions.py.
 */
export const mayAttempt = (role: Role, intent: Intent): boolean =>
  PERMISSION_MATRIX[role]?.[intent] !== "none";

export interface AttendanceResult {
  ok: boolean;
  student_name?: string;
  roll_number?: string;
  class_name?: string | null;
  percentage?: number;
  present_days?: number;
  absent_days?: number;
  late_days?: number;
  total_days?: number;
  recent?: { date: string; status: "present" | "absent" | "late" }[];
  error?: string;
}

export interface EscalationResult {
  ok: boolean;
  ticket_ref?: string;
  target_role?: "teacher" | "management";
  target_name?: string;
  error?: string;
}
