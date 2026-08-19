"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api-client";
import { ROLE_CONFIG } from "@/lib/roles";
import { clearSession, loadSession, saveSession, type StoredSession } from "@/lib/session";
import type { ChatMessage, ChatResponse, Role } from "@/lib/types";
import { AttendanceCard } from "./AttendanceCard";
import { AvatarController, type SpeechPayload } from "./Avatar/AvatarController";
import type { AvatarState } from "./Avatar/AvatarFace";
import { EscalationModal, type EscalationOption } from "./EscalationModal";
import { LanguageSwitcher } from "./LanguageSwitcher";
import { VoiceInput } from "./VoiceInput";

const uid = () => Math.random().toString(36).slice(2);

export function ChatWindow({ role }: { role: Role }) {
  const router = useRouter();
  const config = ROLE_CONFIG[role];

  const [session, setSession] = useState<StoredSession | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [thinking, setThinking] = useState(false);
  const [listening, setListening] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [language, setLanguage] = useState("en");
  const [voiceReplies, setVoiceReplies] = useState(false);
  const [speech, setSpeech] = useState<SpeechPayload | null>(null);
  const [escalationOptions, setEscalationOptions] = useState<EscalationOption[] | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [showTrace, setShowTrace] = useState(false);
  const [lastTrace, setLastTrace] = useState<string[]>([]);

  const scrollRef = useRef<HTMLDivElement>(null);

  // --- session guard ---------------------------------------------------------
  useEffect(() => {
    const stored = loadSession();
    if (!stored) {
      router.replace("/login");
      return;
    }
    if (stored.user.role !== role) {
      router.replace(`/${stored.user.role}`);
      return;
    }
    setSession(stored);
    setLanguage(stored.user.preferred_language || "en");
    setMessages([
      { id: uid(), sender: "assistant", text: config.greeting(stored.user.name) },
    ]);
  }, [role, router, config]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, thinking]);

  const avatarState: AvatarState = listening
    ? "listening"
    : thinking
      ? "thinking"
      : speaking
        ? "speaking"
        : "idle";

  const speak = useCallback(
    async (text: string, lang: string) => {
      if (!voiceReplies || !session || !text) return;
      try {
        const audio = await api.tts(session.token, text, lang);
        setSpeech({ audioBase64: audio.audio_base64, mimeType: audio.mime_type, marks: audio.marks });
      } catch (error) {
        setNotice(
          error instanceof ApiError && error.status === 503
            ? "Spoken replies need Google Cloud credentials on the backend."
            : "Couldn't generate speech for that reply.",
        );
        setVoiceReplies(false);
      }
    },
    [session, voiceReplies],
  );

  const applyResponse = useCallback(
    (result: ChatResponse) => {
      setMessages((current) => [
        ...current,
        {
          id: uid(),
          sender: "assistant",
          text: result.response,
          intent: result.intent,
          data: result.data,
          flags: result.security_flags,
        },
      ]);
      setLastTrace(result.trace);
      if (result.language && result.language !== language) setLanguage(result.language);
      if (result.requires_confirmation && result.data?.kind === "escalation_offer") {
        const offered = (result.data.options as EscalationOption[] | undefined) ?? [
          {
            target_role: String(result.data.target_role ?? "teacher"),
            target_name: String(result.data.target_name ?? "the teacher"),
            recommended: true,
          },
        ];
        setEscalationOptions(offered);
      } else {
        setEscalationOptions(null);
      }
      void speak(result.response, result.language || language);
    },
    [language, speak],
  );

  const send = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || !session || thinking) return;
      setDraft("");
      setNotice(null);
      setMessages((current) => [...current, { id: uid(), sender: "user", text: trimmed }]);
      setThinking(true);
      try {
        applyResponse(await api.chat(session.token, session.sessionId, trimmed));
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          clearSession();
          router.replace("/login");
          return;
        }
        setNotice(error instanceof ApiError ? error.message : "Something went wrong.");
      } finally {
        setThinking(false);
      }
    },
    [session, thinking, applyResponse, router],
  );

  const confirmEscalation = async (confirmed: boolean, targetRole?: string) => {
    if (!session) return;
    setConfirming(true);
    try {
      const result = await api.confirm(session.token, session.sessionId, confirmed, targetRole);
      setEscalationOptions(null);
      applyResponse(result);
    } catch (error) {
      setNotice(error instanceof ApiError ? error.message : "Couldn't submit that request.");
    } finally {
      setConfirming(false);
    }
  };

  const changeLanguage = async (code: string) => {
    setLanguage(code);
    if (!session) return;
    try {
      const user = await api.setLanguage(session.token, code);
      const updated = { ...session, user };
      setSession(updated);
      saveSession(updated);
    } catch {
      setNotice("Couldn't save that language preference.");
    }
  };

  const signOut = () => {
    clearSession();
    router.replace("/login");
  };

  const startFresh = async () => {
    if (!session) return;
    const fresh = await api.newConversation(session.token);
    const updated = { ...session, sessionId: fresh.session_id };
    setSession(updated);
    saveSession(updated);
    setMessages([{ id: uid(), sender: "assistant", text: config.greeting(session.user.name) }]);
    setEscalationOptions(null);
  };

  const suggestions = useMemo(() => config.suggestions, [config]);

  if (!session) return <div className="loading">Loading…</div>;

  return (
    <div className="portal" style={{ ["--accent" as string]: config.accent }}>
      <header className="portal__header">
        <div className="brand">
          <span className="brand__mark">XYZ</span>
          <div>
            <h1>{config.title}</h1>
            <p>{config.persona} · signed in as {session.user.name}</p>
          </div>
        </div>
        <div className="portal__controls">
          <LanguageSwitcher value={language} onChange={changeLanguage} disabled={thinking} />
          <label className="toggle">
            <input
              type="checkbox"
              checked={voiceReplies}
              onChange={(event) => setVoiceReplies(event.target.checked)}
            />
            <span>Speak replies</span>
          </label>
          <button className="button button--ghost" onClick={startFresh}>New chat</button>
          <button className="button button--ghost" onClick={signOut}>Sign out</button>
        </div>
      </header>

      <main className="portal__body">
        <aside className="portal__avatar">
          <AvatarController
            speech={speech}
            baseState={avatarState}
            accent={config.accent}
            label={`XYZ AI ${config.persona}`}
            onSpeakingChange={setSpeaking}
          />
          <div className="portal__avatar-caption">
            <strong>XYZ AI</strong>
            <span>{config.persona}</span>
          </div>
          <button className="link" onClick={() => setShowTrace((v) => !v)}>
            {showTrace ? "Hide" : "Show"} pipeline
          </button>
          {showTrace && (
            <ol className="trace">
              {(lastTrace.length ? lastTrace : ["waiting for a message"]).map((node) => (
                <li key={node}>{node}</li>
              ))}
            </ol>
          )}
        </aside>

        <section className="chat">
          <div className="chat__scroll" ref={scrollRef}>
            {messages.map((message) => (
              <div key={message.id} className={`bubble bubble--${message.sender}`}>
                <p>{message.text}</p>
                {message.data ? <AttendanceCard data={message.data} /> : null}
                {message.flags?.length ? (
                  <span className="bubble__flag">blocked: {message.flags.join(", ")}</span>
                ) : null}
              </div>
            ))}
            {thinking && (
              <div className="bubble bubble--assistant bubble--typing">
                <span /><span /><span />
              </div>
            )}
          </div>

          {notice && <div className="notice">{notice}</div>}

          {messages.length <= 1 && (
            <div className="suggestions">
              {suggestions.map((text) => (
                <button key={text} onClick={() => void send(text)}>{text}</button>
              ))}
            </div>
          )}

          <form
            className="composer"
            onSubmit={(event) => {
              event.preventDefault();
              void send(draft);
            }}
          >
            <input
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder="Ask XYZ AI…"
              aria-label="Message"
              disabled={thinking}
            />
            <VoiceInput
              token={session.token}
              language={language}
              disabled={thinking}
              onListeningChange={setListening}
              onTranscript={(text, detected) => {
                if (detected && detected !== language) setLanguage(detected);
                void send(text);
              }}
              onError={setNotice}
            />
            <button className="button" type="submit" disabled={thinking || !draft.trim()}>
              Send
            </button>
          </form>
        </section>
      </main>

      <EscalationModal
        open={escalationOptions !== null}
        options={escalationOptions ?? []}
        busy={confirming}
        onConfirm={(targetRole) => void confirmEscalation(true, targetRole)}
        onCancel={() => void confirmEscalation(false)}
      />
    </div>
  );
}
