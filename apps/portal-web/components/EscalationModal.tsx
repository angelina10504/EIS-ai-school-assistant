"use client";

export interface EscalationOption {
  target_role: string;
  target_name: string;
  recommended?: boolean;
}

interface Props {
  open: boolean;
  options: EscalationOption[];
  busy?: boolean;
  onConfirm: (targetRole: string) => void;
  onCancel: () => void;
}

const LABEL: Record<string, string> = {
  teacher: "Talk to Teacher",
  management: "Contact School Management",
};

/**
 * The confirmation step is a real gate, not a formality: nothing is written to
 * escalation_requests until the user picks a route here (or types "yes" in chat).
 * Both routes named in the brief are offered, with the one the assistant inferred
 * marked as suggested.
 */
export function EscalationModal({ open, options, busy, onConfirm, onCancel }: Props) {
  if (!open || options.length === 0) return null;

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="escalation-title">
      <div className="modal">
        <h2 id="escalation-title">Who should we reach?</h2>
        <p>Nothing has been sent yet — choose a route and I&apos;ll put the request through.</p>

        <div className="routes">
          {options.map((option) => (
            <button
              key={option.target_role}
              className={`route${option.recommended ? " route--suggested" : ""}`}
              disabled={busy}
              onClick={() => onConfirm(option.target_role)}
            >
              <span className="route__label">
                {LABEL[option.target_role] ?? option.target_role}
                {option.recommended && <span className="route__tag">suggested</span>}
              </span>
              <span className="route__name">{option.target_name}</span>
            </button>
          ))}
        </div>

        <div className="modal__actions">
          <button className="button button--ghost" onClick={onCancel} disabled={busy}>
            {busy ? "Sending…" : "Not now"}
          </button>
        </div>
      </div>
    </div>
  );
}
