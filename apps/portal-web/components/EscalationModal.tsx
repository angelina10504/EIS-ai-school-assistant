"use client";

interface Props {
  open: boolean;
  targetName: string;
  targetRole: string;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

/**
 * The confirmation step is a real gate, not a formality: nothing is written to
 * escalation_requests until the user presses Yes here (or types "yes" in chat).
 */
export function EscalationModal({ open, targetName, targetRole, busy, onConfirm, onCancel }: Props) {
  if (!open) return null;
  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="escalation-title">
      <div className="modal">
        <h2 id="escalation-title">Request a call?</h2>
        <p>
          I can send a call request to <strong>{targetName}</strong>
          {targetRole === "management" ? " (school management)" : " (class teacher)"}. Nothing has
          been sent yet.
        </p>
        <div className="modal__actions">
          <button className="button button--ghost" onClick={onCancel} disabled={busy}>
            Not now
          </button>
          <button className="button" onClick={onConfirm} disabled={busy}>
            {busy ? "Sending…" : "Yes, request the call"}
          </button>
        </div>
      </div>
    </div>
  );
}
