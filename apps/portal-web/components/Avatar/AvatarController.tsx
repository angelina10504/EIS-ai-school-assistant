"use client";

import { useEffect, useRef, useState } from "react";
import type { TTSMark } from "@/lib/types";
import { AvatarFace, type AvatarState } from "./AvatarFace";
import { visemeAt, type Viseme } from "./visemes";

export interface SpeechPayload {
  audioBase64: string;
  mimeType: string;
  marks: TTSMark[];
}

interface Props {
  speech: SpeechPayload | null;
  baseState: AvatarState;
  accent: string;
  label: string;
  onSpeakingChange?: (speaking: boolean) => void;
}

/**
 * Drives mouth shapes off TTS timing marks.
 *
 * Deliberately decoupled from the chat logic: everything it needs is
 * `{ audio, marks[] }`, so it can be exercised without the backend graph.
 */
export function AvatarController({ speech, baseState, accent, label, onSpeakingChange }: Props) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const frameRef = useRef<number | null>(null);
  const [viseme, setViseme] = useState<Viseme>("rest");
  const [speaking, setSpeaking] = useState(false);

  useEffect(() => {
    onSpeakingChange?.(speaking);
  }, [speaking, onSpeakingChange]);

  useEffect(() => {
    if (!speech) return;

    const audio = new Audio(`data:${speech.mimeType};base64,${speech.audioBase64}`);
    audioRef.current = audio;
    const marks = [...speech.marks].sort((a, b) => a.seconds - b.seconds);

    const step = () => {
      const t = audio.currentTime;
      let index = -1;
      for (let i = 0; i < marks.length; i += 1) {
        if (marks[i].seconds <= t) index = i;
        else break;
      }
      if (index < 0) {
        setViseme("closed");
      } else {
        const start = marks[index].seconds;
        const end = marks[index + 1]?.seconds ?? (audio.duration || start + 0.35);
        const progress = end > start ? Math.min(1, (t - start) / (end - start)) : 1;
        setViseme(visemeAt(marks[index].word || "a", progress));
      }
      frameRef.current = requestAnimationFrame(step);
    };

    const stop = () => {
      setSpeaking(false);
      setViseme("rest");
      if (frameRef.current) cancelAnimationFrame(frameRef.current);
      frameRef.current = null;
    };

    audio.addEventListener("ended", stop);
    audio.addEventListener("pause", stop);
    setSpeaking(true);
    frameRef.current = requestAnimationFrame(step);
    void audio.play().catch(() => stop()); // autoplay can be blocked until first interaction

    return () => {
      audio.removeEventListener("ended", stop);
      audio.removeEventListener("pause", stop);
      audio.pause();
      stop();
    };
  }, [speech]);

  return (
    <AvatarFace
      viseme={viseme}
      state={speaking ? "speaking" : baseState}
      accent={accent}
      label={label}
    />
  );
}
