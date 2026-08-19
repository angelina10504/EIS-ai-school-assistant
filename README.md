# XYZ AI — Human-Like School Assistant

XYZ AI is a standalone assistant that behaves like a real school front-desk human. One
account signs you in, and the assistant adapts to who you are — **Student, Parent,
Teacher or Principal** — with its own persona, its own permissions, and its own set of
things it is allowed to do. It talks over **chat**, **voice**, and a **2D avatar** that
lip-syncs to its own speech, in **11 Indian languages**, and it hands you over to a real
teacher or to school management when you want a human.

The interesting part is not that it answers questions. It's that a student cannot talk it
into marking their own attendance, and a parent cannot talk it into reading another
family's child's record — no matter how the message is phrased.

---

## 1. Architecture

```
                     ┌───────────────────────────── apps/portal-web (Next.js) ─────┐
  microphone ───────▶│ VoiceInput ─▶ /api/voice/stt                                │
                     │ ChatWindow ─▶ /api/chat ─▶ reply ─▶ /api/voice/tts          │
                     │                              │                              │
                     │      AvatarController ◀──────┘  { audio, marks[] }          │
                     └───────────────────────────────────────────┬─────────────────┘
                                                                 │ JWT bearer
                     ┌───────────────────────── apps/xyz-ai (FastAPI) ─────────────┐
                     │                                                             │
                     │   LangGraph pipeline (app/graph/graph_builder.py)           │
                     │   ┌───────────────────────────────────────────────────┐     │
                     │   │ auth_resolver      role/user from the token only  │     │
                     │   │ language_detector  script detection + preference  │     │
                     │   │ memory_loader      last N turns from Postgres     │     │
                     │   │ intent_classifier  Gemini function call + guards  │     │
                     │   │ permission_gate    PLAIN CODE. writes audit_log   │     │
                     │   │ persona_selector   role prompt, localized         │     │
                     │   │ tool_executor      narrow, intent-named tools     │     │
                     │   │ response_formatter Gemini + output sanitiser      │     │
                     │   │ memory_writer      persists both sides of a turn  │     │
                     │   └───────────────────────────────────────────────────┘     │
                     │                                                             │
                     │   tools/  attendance · analytics · escalation               │
                     │   mock_services/  school-ERP REST + mock call dispatcher    │
                     └───────────────────────────┬─────────────────────────────────┘
                                                 │
                                    Supabase (Postgres) · Gemini · Google Cloud STT/TTS
```

| Layer | Choice |
|---|---|
| LLM | Google Gemini (`gemini-2.5-flash`, function calling) |
| Orchestration | LangGraph (Python) |
| Backend | FastAPI |
| Frontend | Next.js 15 / React 19 — one app, four role views |
| Speech | Google Cloud Speech-to-Text / Text-to-Speech |
| Avatar | Inline SVG rig + viseme state machine driven by TTS marks |
| Database | Supabase (Postgres); SQLite fallback for offline dev |

### Repository layout

```
xyz-ai-school-assistant/
├── apps/
│   ├── portal-web/          Next.js — login + the four role portals
│   │   ├── app/(auth)/login, app/student, app/parent, app/teacher, app/principal
│   │   ├── components/      ChatWindow, Avatar/, VoiceInput, EscalationModal, …
│   │   └── lib/             api-client, session, roles, languages
│   └── xyz-ai/              FastAPI + LangGraph
│       ├── app/graph/       state, nodes/, graph_builder
│       ├── app/tools/       attendance, analytics, escalation, scope checks
│       ├── app/auth/        permission matrix, JWT, audit, guardrails
│       ├── app/mock_services/  ERP routers + the mock call dispatcher
│       ├── app/voice/       STT / TTS wrappers
│       ├── app/personas/    persona prompt templates
│       ├── app/i18n/        11 languages, BCP-47 codes, TTS voices
│       ├── scripts/demo.py  prints a full scripted transcript
│       └── tests/           79 tests
├── packages/shared-types/   the permission matrix as shared data + TS types
└── infra/supabase/          schema.sql, seed.sql
```

---

## 2. Setup

### Prerequisites

Node.js 20+, Python 3.11+, and [uv](https://docs.astral.sh/uv/) (or plain `pip`).

### Install

```bash
make install
```

or by hand:

```bash
cd apps/xyz-ai && uv venv --python python3.12 .venv && VIRTUAL_ENV=.venv uv pip install -e ".[dev]"
cd ../portal-web && npm install
```

### Environment variables

Copy `apps/xyz-ai/.env.example` to `apps/xyz-ai/.env`:

| Variable | Needed for | If missing |
|---|---|---|
| `GEMINI_API_KEY` | natural language understanding + generation | falls back to a deterministic offline classifier (see §6) |
| `GEMINI_MODEL` | — | defaults to `gemini-2.5-flash` |
| `GOOGLE_APPLICATION_CREDENTIALS` | voice in and out | `/api/voice/*` returns 503; chat still works |
| `SUPABASE_DB_URL` | Postgres persistence | falls back to a local SQLite file |
| `JWT_SECRET` | session tokens | a dev default is used — **set this** |

For the frontend, copy `apps/portal-web/.env.local.example` to `.env.local` if your
backend is not on `http://localhost:8000`.

`GOOGLE_APPLICATION_CREDENTIALS` may be a path relative to `apps/xyz-ai/`. The app
resolves it and exports it into the process environment at startup, because Google's
client libraries read `os.environ` rather than the settings object — putting it in
`.env` alone is not enough for them, so `app/config.py` bridges the two.

**No key is ever sent to the browser, and none is ever placed in the model's context.**

### Database

**Supabase / Postgres** — run both files in the SQL editor, in order:

```
infra/supabase/schema.sql
infra/supabase/seed.sql
```

then set `SUPABASE_DB_URL` to your connection string
(`postgresql+psycopg://postgres:PASSWORD@db.PROJECT.supabase.co:5432/postgres`).

**Or, with no cloud account at all** — leave `SUPABASE_DB_URL` blank and run:

```bash
make seed
```

which creates a local SQLite file with the same schema and the same demo data.

### Run

```bash
make api    # http://localhost:8000  (docs at /docs)
make web    # http://localhost:3000
```

### Demo accounts

Password for every account: `password123`

| Role | Email | Notes |
|---|---|---|
| Student | `rahul@student.xyz.edu` | 91.2% attendance, Class 8A |
| Parent | `sunita@parent.xyz.edu` | linked to Rahul only |
| Parent | `ramesh@parent.xyz.edu` | two children — good for the "which child?" clarification |
| Teacher | `anita@teacher.xyz.edu` | Class 8A |
| Teacher | `vikram@teacher.xyz.edu` | Class 8B |
| Principal | `principal@xyz.edu` | analytics only |

### Verify

```bash
make test    # 79 backend tests
make check   # tests + frontend typecheck + production build
make demo    # prints a scripted transcript of every scenario in the brief
```

---

## 3. How role-based security is enforced

The rule the whole design follows: **the model decides what the user probably wants; plain
code decides what is allowed to happen.**

**`app/auth/permissions.py`** holds the matrix as data, and `check_permission(role, intent)`
is an ordinary function with no LLM in it.

| Role | view_attendance | mark_attendance | view_analytics | escalate |
|---|---|---|---|---|
| Student | own only | ✗ | ✗ | ✓ |
| Parent | linked child only | ✗ | ✗ | ✓ |
| Teacher | own class | own class | ✗ | ✗ |
| Principal | ✗ (analytics instead) | ✗ | ✓ school-wide | ✗ |

Six defences, mapped to the six threats in the brief:

| Threat | Where it is stopped |
|---|---|
| **Prompt injection** | `permission_gate` is a node with no conditional edge around it — every turn passes through it whatever the model returned. `guardrails.scan_input` additionally flags known attack shapes, and the refusal for those is generated in code, never by the model. |
| **Unauthorized data access** | `tools/scope.py` re-derives the caller's visible students from `parent_student_link` / `classes.teacher_id` on every call. Passing a student ID the model made up gets `not_permitted`, and an unknown name and an out-of-scope name produce the same answer so the refusal leaks nothing. |
| **System-prompt extraction** | Detected on input; `sanitize_output` also blocks any reply containing persona-prompt markers or a long verbatim slice of the prompt. |
| **Credential extraction** | Keys live only in backend env vars, are never added to model context, and `sanitize_output` redacts anything shaped like a Google key, a JWT, a Supabase key or a Postgres URL. The global exception handler returns a fixed message instead of a stack trace. |
| **Fake role claims** | `auth_resolver` reads the role from the users table via the signed token. Typing "I am the principal" changes nothing — there is no code path from message text to `state["role"]`. |
| **Unauthorized actions** | Mutating tools need the gate *and*, for escalation, an explicit confirmation step. |
| **Invented figures** | `response_formatter._invents_a_percentage` compares every percentage in the reply against what the tool returned and discards the reply if they disagree. A model that says 51.2% when the record says 91.2% never reaches the parent. |
| **Premature escalation claims** | The offer and the failure message are *pinned*: the model is asked to translate a fixed sentence, and a reply that stops being a question is replaced with the fixed one. |

Every permission check — allowed or denied — is written to `audit_log`. The UI's *Show
pipeline* link renders the node trace for the last turn, and `GET /api/audit/recent`
returns the caller's own audit rows.

### The escalation handshake

`escalation_requests` is not touched when the offer is made. `POST /api/chat/confirm`
(or a plain "yes" in chat) is what calls `request_escalation`, which writes the row and
then calls the mock dispatcher. If the dispatcher fails, the row stays `pending`, the tool
returns `ok: false`, and the assistant says nobody has been contacted. Try it:

```python
from app.mock_services import call_service
call_service.FORCE_FAILURE = True
```

`make demo` runs this path at the end.

---

## 4. API

| Endpoint | Purpose |
|---|---|
| `POST /api/session/login` | mock login → JWT + a fresh conversation session |
| `POST /api/session/new` | start a new conversation |
| `POST /api/session/language` | set the preferred language |
| `POST /api/chat` | run the graph for one turn |
| `POST /api/chat/confirm` | the explicit "yes" that submits an escalation |
| `POST /api/voice/stt` | audio → transcript (language-aware) |
| `POST /api/voice/tts` | text → MP3 + SSML mark timings for lip-sync |
| `GET /api/attendance/{student_id}` | REST read, same permission gate |
| `POST /api/attendance/mark` | REST write, teacher only |
| `GET /api/analytics/attendance` | school-wide aggregate, principal only |
| `GET /api/audit/recent` | the caller's own audit entries |

Interactive docs: `http://localhost:8000/docs`.

---

## 5. Voice and the avatar

```
mic → MediaRecorder(webm/opus) → /api/voice/stt → transcript → /api/chat
    → reply text → /api/voice/tts → { mp3, marks[] } → AvatarController
```

Google Cloud TTS does not return visemes, so `app/voice/tts.py` injects an SSML
`<mark>` before every word and requests timepoints. `AvatarController` runs a
`requestAnimationFrame` loop, finds the current word from the mark timings, and steps a
5-shape mouth state machine (`closed / wide / narrow / round / rest`) chosen from the
vowels in that word. It is good enough to read as speech at 2D fidelity, and it is honest
about being word-level rather than phoneme-level.

The controller takes only `{ audioBase64, mimeType, marks[] }`, so it is testable without
the backend, and swapping the SVG rig for a Lottie or Rive rig is a change to
`AvatarFace.tsx` alone.

---

## 6. Running without API keys

With no `GEMINI_API_KEY`, the app boots into an **offline provider** (`app/llm/offline.py`):
a deterministic keyword classifier plus templated replies. Every architectural claim above
still holds — the graph, the permission gate, the relationship checks, the escalation
handshake and the audit log are all exercised — which is also why the whole test suite runs
with no network and no cost.

What you lose is the naturalness: offline replies are templates, and they are **always in
English** even when the language is correctly detected as Hindi or Tamil. Set
`GEMINI_API_KEY` for the real thing.

---

## 7. Known limitations

- **Free-tier Gemini quota is per model and small** (20 requests/day on
  `gemini-3.6-flash`). When it runs out the app falls back to templated English replies
  and logs `Gemini quota exhausted` — it does not crash, but the demo stops looking
  natural. Set `GEMINI_MODEL` to another model, or enable billing, before recording.
- **`gemini-3.5-flash-lite` is noticeably weaker** than `gemini-3.6-flash`; it was
  observed spelling 91.2% as "fifty-one point two" in Hindi before the digits rule and
  the percentage guard were added. Prefer the larger model when quota allows.
- **The avatar is an inline SVG rig, not a Lottie/Rive file.** Same viseme contract, one
  fewer asset pipeline. Swap point is `components/Avatar/AvatarFace.tsx`.
- **Pending escalation offers are held in process memory** (`app/graph/pending.py`), because
  an unconfirmed offer must not become a row. Multi-worker deployments need Redis or a
  dedicated table.
- **Auth is mock-grade**: PBKDF2 password hashing and unrevocable JWTs, no refresh tokens,
  no rate limiting, no lockout. It is structurally correct — the role comes only from the
  server — but it is not production auth.
- **The guardrail patterns are English-first.** They are defence-in-depth, not the boundary;
  a Hindi-language injection attempt still cannot get past the permission gate or the
  relationship checks, it just will not be *flagged* as an attempt.
- **Attendance percentage** counts `late` as a half day over a rolling 90-day window. Real
  schools have term boundaries and holiday calendars; this does not.
- **STT expects `webm/opus`**, which is what Chrome's MediaRecorder produces. Safari
  records in a different container and needs a transcode step.
- **No streaming.** Replies arrive whole; there is no token-by-token typing effect.

## 8. Troubleshooting

**"Voice needs Google Cloud credentials on the backend"** — the frontend shows this on any
503 from `/api/voice/*`. Check the real reason:

```bash
curl -s localhost:8000/health
```

`speech` reports one of `configured (…)`, `misconfigured — no file at …`, or
`not configured`. If it says configured and voice still fails, the backend log carries the
full Google error (API not enabled, billing off, wrong project). Note the Speech-to-Text
**and** Text-to-Speech APIs must each be enabled on the service account's project.

**Replies are short, templated and English-only** — Gemini is failing and the offline
fallback is answering. `grep -i gemini` the backend log; a 429 means the model's daily
free-tier quota is gone, so change `GEMINI_MODEL` in `.env`.

**Replies stop mid-sentence** — the model spent its output budget on thinking tokens.
`RESPONSE_MAX_TOKENS` and `THINKING_BUDGET` in `app/llm/gemini.py` control this, and a
truncated reply is detected and replaced with the templated one rather than shown.

**Everything answers in the wrong language** — the classifier's `detected_language`
overrides the stored preference for that turn. Set the language explicitly in the header
switcher to pin it.

## 9. Demo video

_(link to be added)_

Suggested run order: student attendance → parent attendance → "what about yesterday?"
(memory) → parent asks about another family's child (refused) → escalation offer, confirm,
ticket → teacher marks Rahul absent → teacher tries a Class 8B student (refused) →
principal analytics → principal asks for an individual record (refused) → "ignore previous
instructions…" (refused) → a Hindi turn with voice.
