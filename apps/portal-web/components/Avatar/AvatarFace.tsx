"use client";

import type { Viseme } from "./visemes";

export type AvatarState = "idle" | "listening" | "thinking" | "speaking";

interface Props {
  viseme: Viseme;
  state: AvatarState;
  accent: string;
  label: string;
}

/**
 * The rig. Swapping this for a Lottie or Rive component is a one-file change —
 * AvatarController only ever hands it a viseme and a state.
 */
const MOUTHS: Record<Viseme, { rx: number; ry: number; y: number }> = {
  rest: { rx: 13, ry: 3.5, y: 122 },
  closed: { rx: 12, ry: 1.6, y: 122 },
  narrow: { rx: 11, ry: 6, y: 122 },
  wide: { rx: 18, ry: 11, y: 123 },
  round: { rx: 9, ry: 10, y: 123 },
};

export function AvatarFace({ viseme, state, accent, label }: Props) {
  const mouth = MOUTHS[state === "speaking" ? viseme : "rest"];
  const eyeY = state === "thinking" ? 92 : 94;

  return (
    <div className={`avatar avatar--${state}`} aria-label={`${label}, ${state}`} role="img">
      <svg viewBox="0 0 200 200" width="100%" height="100%">
        <defs>
          <radialGradient id="halo" cx="50%" cy="45%" r="55%">
            <stop offset="0%" stopColor={accent} stopOpacity="0.30" />
            <stop offset="100%" stopColor={accent} stopOpacity="0" />
          </radialGradient>
          <linearGradient id="skin" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#f6d5bd" />
            <stop offset="100%" stopColor="#e7b795" />
          </linearGradient>
        </defs>

        <circle cx="100" cy="100" r="96" fill="url(#halo)" />
        <circle className="avatar__pulse" cx="100" cy="100" r="74" fill="none" stroke={accent} strokeWidth="2" />

        {/* shoulders */}
        <path d="M40 200 Q100 148 160 200 Z" fill={accent} opacity="0.85" />
        {/* head */}
        <ellipse cx="100" cy="100" rx="46" ry="52" fill="url(#skin)" />
        {/* ears */}
        <ellipse cx="54" cy="104" rx="6" ry="10" fill="#e7b795" />
        <ellipse cx="146" cy="104" rx="6" ry="10" fill="#e7b795" />
        {/* hair, drawn over the skull so it reads as a hairline */}
        <path d="M54 100 Q54 48 100 48 Q146 48 146 100 Q142 72 100 70 Q58 72 54 100 Z" fill="#2f2a3d" />
        <path d="M54 100 Q50 78 60 66 Q56 88 58 102 Z" fill="#2f2a3d" />
        <path d="M146 100 Q150 78 140 66 Q144 88 142 102 Z" fill="#2f2a3d" />

        {/* eyes */}
        <g className="avatar__eyes">
          <ellipse cx="83" cy={eyeY} rx="6.5" ry="7.5" fill="#2f2a3d" />
          <ellipse cx="117" cy={eyeY} rx="6.5" ry="7.5" fill="#2f2a3d" />
          <circle cx="85" cy={eyeY - 2.5} r="2" fill="#fff" opacity="0.9" />
          <circle cx="119" cy={eyeY - 2.5} r="2" fill="#fff" opacity="0.9" />
        </g>
        {/* brows lift a little when thinking */}
        <path
          d={state === "thinking" ? "M74 80 Q83 74 92 79" : "M74 82 Q83 78 92 81"}
          stroke="#2f2a3d"
          strokeWidth="3"
          fill="none"
          strokeLinecap="round"
        />
        <path
          d={state === "thinking" ? "M108 79 Q117 74 126 80" : "M108 81 Q117 78 126 82"}
          stroke="#2f2a3d"
          strokeWidth="3"
          fill="none"
          strokeLinecap="round"
        />

        <path d="M100 100 Q104 110 99 112" stroke="#c98f6d" strokeWidth="2.5" fill="none" strokeLinecap="round" />

        {/* mouth */}
        <ellipse cx="100" cy={mouth.y} rx={mouth.rx} ry={mouth.ry} fill="#8d3f47" />
        {mouth.ry > 4 && <ellipse cx="100" cy={mouth.y - mouth.ry / 2.2} rx={mouth.rx * 0.7} ry={mouth.ry * 0.28} fill="#fff" opacity="0.85" />}
      </svg>

      {state === "listening" && (
        <div className="avatar__badge avatar__badge--listening">Listening…</div>
      )}
      {state === "thinking" && <div className="avatar__badge">Thinking…</div>}
    </div>
  );
}
