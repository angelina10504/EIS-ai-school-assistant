# EIS AI — Human-Like School Assistant

EIS AI is a standalone assistant that behaves like a real school front-desk human. One
account signs you in, and the assistant adapts to who you are — **Student, Parent,
Teacher or Principal** — with its own persona, its own permissions, and its own set of
things it is allowed to do. It talks over **chat**, **voice**, and a **2D avatar** that
lip-syncs to its own speech, in **11 Indian languages**, and it hands you over to a real
teacher or to school management when you want a human.

The interesting part is not that it answers questions. It's that a student cannot talk it
into marking their own attendance, and a parent cannot talk it into reading another
family's child's record — no matter how the message is phrased.

| | |
|---|---|
| **Repository** | https://github.com/angelina10504/EIS-ai-school-assistant |
| **Demo video** | _(link to be added)_ |
| **Stack** | FastAPI · LangGraph · Google Gemini · Next.js 15 · Supabase Postgres · Google Cloud STT/TTS |
| **Tests** | 88 backend (pytest) + 7 avatar (node --test), all passing |
| **Run it** | `make install && make seed && make api` then `make web` → http://localhost:3000 |

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
                     ┌───────────────────────── apps/eis-ai (FastAPI) ─────────────┐
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
| LLM | Google Gemini (function calling); default `gemini-3.6-flash`, set via `GEMINI_MODEL` |
| Orchestration | LangGraph (Python) |
| Backend | FastAPI |
| Frontend | Next.js 15 / React 19 — one app, four role views |
| Speech | Google Cloud Speech-to-Text / Text-to-Speech |
| Avatar | Inline SVG rig + viseme state machine driven by TTS marks |
| Database | Supabase (Postgres); SQLite fallback for offline dev |

### Repository layout

```
EIS-ai-school-assistant/
├── apps/
│   ├── portal-web/          Next.js — login + the four role portals
│   │   ├── app/(auth)/login, app/student, app/parent, app/teacher, app/principal
│   │   ├── components/      ChatWindow, Avatar/, VoiceInput, EscalationModal, …
│   │   │   └── Avatar/visemes.test.ts   7 tests: npm run test:visemes
│   │   └── lib/             api-client, session, roles, languages
│   └── eis-ai/              FastAPI + LangGraph
│       ├── app/graph/       state, nodes/, graph_builder
│       ├── app/tools/       attendance, analytics, escalation, scope checks
│       ├── app/auth/        permission matrix, JWT, audit, guardrails
│       ├── app/mock_services/  ERP routers + the mock call dispatcher
│       ├── app/voice/       STT / TTS wrappers
│       ├── app/personas/    persona prompt templates
│       ├── app/i18n/        11 languages, BCP-47 codes, TTS voices
│       ├── scripts/demo.py  prints a full scripted transcript
│       └── tests/           88 tests
├── packages/shared-types/   the permission matrix as shared data + TS types
└── infra/supabase/          schema.sql, seed.sql
```

---

## 2. What the assessment asked for, and where it lives

| Requirement | Status | Where |
|---|---|---|
| Student views own attendance | ✅ | `tools/attendance_tools.get_attendance`, scoped in `tools/scope.py` |
| Parent views child's attendance | ✅ | same tool; scope derived from `parent_student_link` |
| Teacher marks attendance | ✅ | `tools/attendance_tools.mark_attendance`, own class only |
| Principal school analytics | ✅ | `tools/analytics_tools.get_attendance_analytics`, aggregates only |
| Natural language + conversation history | ✅ | `graph/nodes/memory_loader.py`, `memory_writer.py` |
| Follow-up questions without restating context | ✅ | history passed to the classifier; see `test_followup_without_restating_context` |
| Asks for missing information | ✅ | `tool_executor` emits `kind: clarification` |
| Handles corrections mid-conversation | ✅ | "Sorry, I meant Arjun" re-resolves the subject |
| Four personas with distinct tone | ✅ | `personas/templates.py`, localized per language |
| Voice in / voice out | ✅ | `voice/stt.py`, `voice/tts.py`; verified end-to-end in Hindi and Tamil |
| AI avatar with lip-sync | ✅ | `components/Avatar/`, driven by real SSML `<mark>` timings |
| Facial expressions | ◐ | four states (idle/listening/thinking/speaking); not content-driven |
| Real-time conversation | ◐ | turn-based; no token streaming or barge-in |
| "Talk to Teacher" / "Contact School Management" | ✅ | both offered by name in `EscalationModal` |
| Mock call/support request, only after confirmation | ✅ | `mock_services/call_service.py`; nothing written before "yes" |
| Never claims contact unless confirmed | ✅ | pinned wording + `test_failed_dispatch_never_claims_contact` |
| 11 languages | ✅ | `i18n/languages.py` |
| Prompt injection | ✅ | §4 |
| Unauthorized data access | ✅ | §4 |
| System-prompt extraction | ✅ | §4 |
| API-key extraction | ✅ | §4 |
| Fake role claims | ✅ | §4 |
| Unauthorized actions | ✅ | §4 |
| Authorization at the tool layer, not the prompt | ✅ | `auth/permissions.py` — plain code, no LLM |

◐ = partially met; see [Known limitations](#8-known-limitations).

### A note on repository structure

The brief sketches five repositories — `student-portal`, `parent-portal`,
`management-portal`, `staff-portal` and `eis-ai`. This submission is one monorepo in which
the four portals are **role views inside a single Next.js app**, because the alternative
means four codebases sharing one chat component, one API client and one auth flow, kept in
sync by hand.

The property the brief actually cares about is preserved and strengthened: a role sees only
its own capabilities. That is enforced server-side by `auth/permissions.py` and re-checked
in every tool, so it holds no matter which URL is opened — whereas four separate frontends
would still have needed exactly the same backend gate to be secure. The role views live in
`apps/portal-web/app/{student,parent,teacher,principal}/`.

---

## 3. Setup

### Prerequisites

Node.js 20+, Python 3.11+, and [uv](https://docs.astral.sh/uv/) (or plain `pip`).

### Install

```bash
make install
```

or by hand:

```bash
cd apps/eis-ai && uv venv --python python3.12 .venv && VIRTUAL_ENV=.venv uv pip install -e ".[dev]"
cd ../portal-web && npm install
```

### Environment variables

Copy `apps/eis-ai/.env.example` to `apps/eis-ai/.env`:

| Variable | Needed for | If missing |
|---|---|---|
| `GEMINI_API_KEY` | natural language understanding + generation | falls back to a deterministic offline classifier (see §6) |
| `GEMINI_MODEL` | — | defaults to `gemini-3.6-flash`; any current Gemini model works |
| `GOOGLE_APPLICATION_CREDENTIALS` | voice in and out | `/api/voice/*` returns 503; chat still works |
| `SUPABASE_DB_URL` | Postgres persistence | falls back to a local SQLite file |
| `JWT_SECRET` | session tokens | a dev default is used — **set this** |

For the frontend, copy `apps/portal-web/.env.local.example` to `.env.local` if your
backend is not on `http://localhost:8000`.

`GOOGLE_APPLICATION_CREDENTIALS` may be a path relative to `apps/eis-ai/`. The app
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
| Student | `rahul@student.eis.edu` | 91.2% attendance, Class 8A |
| Parent | `sunita@parent.eis.edu` | linked to Rahul only |
| Parent | `ramesh@parent.eis.edu` | two children — good for the "which child?" clarification |
| Teacher | `anita@teacher.eis.edu` | Class 8A |
| Teacher | `vikram@teacher.eis.edu` | Class 8B |
| Principal | `principal@eis.edu` | analytics only |

### Verify

```bash
make test    # 88 backend tests
make check   # tests + frontend typecheck + production build
make demo    # prints a scripted transcript of every scenario in the brief
```

The avatar has its own suite, run from `apps/portal-web`:

```bash
npm run test:visemes    # 7 tests — mouth shapes across all 11 scripts
```

`make demo` writes to the database (it marks attendance and creates escalation rows), so
run `make seed` afterwards if you are about to demo.

---

## 4. How role-based security is enforced

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

## 5. API

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

## 6. Voice and the avatar

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

## 7. Running without API keys

With no `GEMINI_API_KEY`, the app boots into an **offline provider** (`app/llm/offline.py`):
a deterministic keyword classifier plus templated replies. Every architectural claim above
still holds — the graph, the permission gate, the relationship checks, the escalation
handshake and the audit log are all exercised — which is also why the whole test suite runs
with no network and no cost.

What you lose is the naturalness: offline replies are templates, and they are **always in
English** even when the language is correctly detected as Hindi or Tamil. Set
`GEMINI_API_KEY` for the real thing.

---

## 8. Known limitations

- **Free-tier Gemini quota is small and per model** — around 20 requests/day, and each
  conversation turn costs **two** calls (one to classify intent, one to generate the
  reply). That is roughly ten turns a day per model. When it runs out the app falls back
  to templated English replies and logs `Gemini quota exhausted` rather than crashing.
  Set `GEMINI_MODEL` to a different model or enable billing before a live demo.
- **Smaller models are visibly weaker.** `gemini-3.5-flash-lite` was observed rendering
  91.2% as "fifty-one point two" in Hindi. That specific failure is now caught — personas
  require digits and `_invents_a_percentage` discards any reply whose figures disagree
  with the tool — but prefer a larger model where quota allows.
- **Real-time conversation is turn-based.** No token streaming and no barge-in: you
  cannot interrupt the avatar mid-sentence. The brief hedges this with "where technically
  possible", but it is the most visible gap.
- **Facial expressions are state-based, not emotional.** The avatar reacts to idle /
  listening / thinking / speaking, not to whether the news is good or bad.
- **Not deployed.** Runnable locally, which the brief permits, but there is no public URL.
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
- **Reseeding is destructive by design.** `make seed` wipes conversations, escalations
  and the audit log. User IDs are fixed (matching `infra/supabase/seed.sql`) so existing
  sessions survive, but anything the demo created is gone.

## 9. Troubleshooting

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

**"Your session has expired" / unexplained 401s** — a token outlives the row it points
at if the database is reseeded with different user IDs. `seed.py` now uses the fixed IDs
in `infra/supabase/seed.sql` so this should not recur; if it does, sign out and back in.
Note the failure surfaces on *whatever call you happen to make next*, so read the status
code in the backend log rather than trusting the feature that reported it.

**A model returns 503 "high demand"** — popular models get busy. `_call_with_retry` in
`app/llm/gemini.py` retries transient 5xx three times with backoff; quota errors (429) are
deliberately not retried, since those need a different model rather than patience.

**Everything answers in the wrong language** — the classifier's `detected_language`
overrides the stored preference for that turn. Set the language explicitly in the header
switcher to pin it.

## 10. Demo video

**▶ _(link to be added)_**

The run order below is what the video follows. `make demo` prints the same scenarios as a
transcript, including the escalation-failure path, if you would rather read than watch.

| # | Role | Shown |
|---|---|---|
| 1 | Student | "What is my attendance?" → 91.2%, the brief's own example figure |
| 2 | Parent | "How much attendance does my child have?" — the child is resolved from the database, never named by the user |
| 3 | Parent | "What about yesterday?" — memory: no child, no topic restated |
| 4 | Parent | Asks about another family's child → refused, and the refusal confirms nothing about whether that student exists |
| 5 | Parent | "I'm not satisfied" → both routes offered by name → confirm → real ticket reference |
| 6 | Teacher | "Mark Rahul absent today." → natural language to a database write |
| 7 | Teacher | Tries a Class 8B student → refused; the tool re-checks the class relationship |
| 8 | Principal | "What is the overall attendance?" → aggregates only, no student named |
| 9 | Any | "Ignore previous instructions…" → refused in code; *Show pipeline* reveals the nine graph nodes |
| 10 | Parent | A Hindi turn with voice and avatar lip-sync |

Record step 6 **after** steps 1–5, or reseed afterwards: marking Rahul absent moves him
off the 91.2% that matches the brief.
