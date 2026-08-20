"use client";

import { useRef, useState } from "react";
import { api, ApiError } from "@/lib/api-client";

interface Props {
  token: string;
  language: string;
  disabled?: boolean;
  onTranscript: (text: string, language: string) => void;
  onListeningChange?: (listening: boolean) => void;
  onError?: (message: string) => void;
  onAuthExpired?: () => void;
}

/** Mic → MediaRecorder → /api/voice/stt → transcript handed back to the chat. */
export function VoiceInput({
  token,
  language,
  disabled,
  onTranscript,
  onListeningChange,
  onError,
  onAuthExpired,
}: Props) {
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  const [listening, setListening] = useState(false);
  const [busy, setBusy] = useState(false);

  const setState = (value: boolean) => {
    setListening(value);
    onListeningChange?.(value);
  };

  const start = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, { mimeType: "audio/webm;codecs=opus" });
      chunksRef.current = [];
      recorder.ondataavailable = (event) => chunksRef.current.push(event.data);
      recorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        if (blob.size < 1200) return; // a stray click, not speech
        setBusy(true);
        try {
          const result = await api.stt(token, blob, language);
          if (result.transcript) onTranscript(result.transcript, result.language);
          else onError?.("I didn't catch that — could you try again?");
        } catch (error) {
          // Report what actually went wrong. Blaming speech recognition for an
          // expired session sends you debugging the microphone for an hour.
          if (error instanceof ApiError && error.status === 401) {
            onAuthExpired?.();
            onError?.("Your session has expired — please sign in again.");
          } else if (error instanceof ApiError && error.status === 503) {
            onError?.("Voice needs Google Cloud credentials on the backend. You can still type.");
          } else if (error instanceof ApiError && error.status === 0) {
            onError?.("Can't reach the backend. Is it running on port 8000?");
          } else if (error instanceof ApiError) {
            onError?.(`Speech recognition failed (${error.status}): ${error.message}`);
          } else {
            onError?.("Speech recognition failed. You can still type.");
          }
        } finally {
          setBusy(false);
        }
      };
      recorder.start();
      recorderRef.current = recorder;
      setState(true);
    } catch {
      onError?.("I couldn't access the microphone. Check the browser permission.");
    }
  };

  const stop = () => {
    recorderRef.current?.stop();
    recorderRef.current = null;
    setState(false);
  };

  return (
    <button
      type="button"
      className={`mic ${listening ? "mic--live" : ""}`}
      onClick={listening ? stop : start}
      disabled={disabled || busy}
      aria-pressed={listening}
      title={listening ? "Stop recording" : "Speak to XYZ AI"}
    >
      {busy ? "…" : listening ? "■" : "🎙"}
      <span className="mic__label">{listening ? "Stop" : busy ? "Transcribing" : "Speak"}</span>
    </button>
  );
}
