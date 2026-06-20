# Nomos Clearing-Calls Agent — Runbook

AI voice agent that phones a German grid operator's back-office clerk, clears a stuck
market-communication case, and closes the loop (structured data + German note + next
action). See `README.md` for the challenge brief and `CHEATSHEET.md` for the domain.

## Architecture (what's built)

```
Dashboard (web/index.html)
   │  POST /calls {case_id}
   ▼
FastAPI orchestrator (app/)
   │  Twilio originates the call (ONLY to the practice number — enforced in code)
   ▼
Twilio  ──navigate IVR, send DTMF──▶  bridge media  ──▶  ElevenLabs Conversational AI agent
   │                                                         │ German conversation, prompt-driven
   │   live server-tools (POST /tools/*)  ◀───────────────── │ validate_id · record_finding · end_call
   ▼
EL post-call webhook (POST /elevenlabs/post-call)
   │  finalize: findings → fixed JSON schema → plain-German note (+EN gloss) → mock triggers
   ▼
Store (data/) + dashboard shows result · note · triggered action
```

Key modules:
- `app/digits.py` — pre-spells every ID into German digit tokens (the make-or-break feature).
- `app/agent_prompt.py` — the agent brain: 4-phase flow, AI-disclosure-first, never-fabricate, digit readback, fallback playbook.
- `app/telephony.py` — Twilio origination + IVR-navigating TwiML; `assert_dialable` compliance gate.
- `app/tools_routes.py` + `app/validation.py` — the live tools (validate_id is a local checksum).
- `app/finalize.py` / `app/notes.py` / `app/triggers.py` — close the loop.
- `sim/` — the Helga clerk simulator (personas + curveballs + LLM harness).

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # fill in the values below
```

`.env` essentials:
- `PRACTICE_CLERK_NUMBER` — the Nomos practice clerk (the ONLY number the agent will dial).
- `TWILIO_*` — account SID, auth token, from-number.
- `ELEVENLABS_API_KEY`, `ELEVENLABS_AGENT_ID` (+ `ELEVENLABS_PHONE_NUMBER_ID` for native outbound).
- `PUBLIC_BASE_URL` — your public https URL (e.g. ngrok) so Twilio + EL can reach the webhooks.

## Run

```bash
uvicorn app.main:app --reload          # backend + dashboard at http://localhost:8000
```

### Frontend (React + TypeScript + Vite — `frontend/`)

The dashboard is a React + TypeScript app. FastAPI serves the **built** bundle at `/`
automatically (falling back to the legacy single-file `web/index.html` if no build exists).

```bash
cd frontend && npm install

# Dev: hot-reload UI on :5173, API proxied to FastAPI on :8000 (run both)
npm run dev

# Type-check only
npm run typecheck

# Prod: type-check + build; FastAPI then serves frontend/dist at http://localhost:8000
npm run build
```

Layout of `frontend/src/`:
- `styles.css` — design tokens (palette, type scale).
- `lib/types.ts` — **shared types mirroring the backend** (`app/schema.py`,
  `app/fixtures.py`): `CaseSummary`, `CaseVariables`, `CallResult`, etc. Keep in sync with Python.
- `lib/api.ts` — all backend calls, isolated; point the UI at another backend in one file.
- `lib/digits.ts` — German digit spelling (mirrors `app/digits.py`).
- `components/Digits.tsx` — the digit-tile signature; plus `CaseCard`, `LiveCall`,
  `Outcome`, `Preview`, and `App.tsx`.

Push the agent config to ElevenLabs (after editing the prompt, or to set the voice):

```bash
python -m scripts.sync_agent                 # prompt + tools + first message + language=de
python -m scripts.sync_agent <voice_id>      # also set the chosen German voice
```

## Develop without burning the practice number — the Helga simulator

```bash
python -m sim.dump CASE-A                     # print the clerk prompt
python -m sim.dump CASE-C off_by_one          # a curveball variant

export OPENAI_API_KEY=...                      # the harness plays both sides with an OpenAI model
python -m sim.harness CASE-A                   # full conversation, happy path
python -m sim.harness CASE-C off_by_one        # robustness curveball
```

Curveballs available: `happy`, `off_by_one`, `cant_find`, `transfer`, `voicemail`,
`asks_unknown`, `other_supplier` (see `sim/personas.py`).

## Voice A/B (the first-10-seconds warmth)

```bash
python -m scripts.voice_ab <voiceA> <voiceB>   # renders the opener + a digit readback
# listen to data/voice_ab/*.mp3, then:
python -m scripts.sync_agent <winning_voice_id>
```
Pick German-NATIVE voices (not an English voice speaking German).

## Tests

```bash
python -m pytest -q          # 44 tests: digits, personas, telephony, tools, pipeline, robustness, dashboard
```

## Final live validation (needs creds + practice number)

For each of CASE-A, CASE-C, CASE-B:
1. `POST /calls {"case_id": "CASE-A"}` (dashboard "Start call", dry-run off).
2. Listen: agent navigates the menu, declares it is an AI as its first words to the human,
   offers the 4 facts, reads the MaLo digit by digit.
3. Confirm it captures the right outcome (CASE-A: meter ausgebaut → new Anlage; CASE-C:
   corrected MaLo read back; CASE-B: Vorgangsnummer + no resubmission).
4. Check the dashboard: structured result + German note + triggered action.

Compliance (enforced in code + prompt, never disable):
- AI-disclosure is the agent's first words to a human (EU AI Act).
- Synthetic data only; the agent dials ONLY the configured practice number.
```
