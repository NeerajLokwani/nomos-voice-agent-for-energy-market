# Nomos "Clearing Calls" — AI Voice Agent for the German Energy Market

## Context

Hackathon challenge (Nomos): build an AI voice agent that autonomously phones a German
grid operator's back-office clerk ("Helga"), clears a stuck market-communication (MaKo)
case, and feeds the result back into Nomos' automated workflows.

The repo currently contains **only the brief and data** — no code yet:
- `README.md`, `CHEATSHEET.md` — domain + rules
- `fixtures.json` — 3 synthetic cases (CASE-A bounced registration, CASE-B reminder/Vorgangsnummer,
  CASE-C MaLo-Ident / corrected number)
- `recordings/example-{1,2,3}-*.md` — gold-standard call transcripts

**The bar (from the brief):**
- Helga, 54, must be *happy to talk to the agent and not hang up in the first 10 seconds* — warm,
  genuinely human German, slows down, reads long numbers back **one digit at a time** (the #1
  differentiator the brief says most agents fail).
- A call = navigate an **automated IVR** (press keypad digit) → reach a human → declare it's an AI
  (EU AI Act, *first words to a person*) → state the case + offer the 4 facts proactively →
  capture the clerk's diagnosis, reading any number back digit-by-digit → close politely (~2 min).
- "Winning" = **real reason + correct next step**, not just a ticket number (CASE-A); sometimes a
  Vorgangsnummer is the win (CASE-B).
- Then: extract facts → **structured data** → **plain-German back-office note** → **trigger next action**.
- Hard rules: **AI-disclosure first**; **synthetic data only**, only ever dial the **practice clerk
  number**, never a real grid operator.

## Design decisions (resolved with user)

| Area | Decision |
|---|---|
| Voice loop | **ElevenLabs Conversational AI** (bundled STT/LLM/TTS + barge-in + Twilio integration) |
| Topology | **Thick orchestrator** (Python/FastAPI) behind the EL agent, with **live server-tools** |
| Live tools | `record_finding`/`update_case`, `validate_id`, `end_call`/`handoff_trigger` are primary; `get_case_context` only as a **redundant safety net** (case normally passed via dynamic variables) |
| IVR/DTMF | Handle in the **Twilio call-control layer** (send DTMF before bridging to EL; menu is known) |
| Number reading | **Pre-format every ID into spaced German digit tokens** in code (never trust raw TTS) |
| Close the loop | **Mocked-but-real services + visible artifacts** (no real market contact) |
| Dev/test | **Build a "Helga" clerk simulator** (EL agent / LLM persona per case); reserve real number for final runs |
| Case scope | **One case-agnostic agent** driven by dynamic variables; build order **A → C → B** |
| Robustness | **Explicit fallback playbook + never-fabricate guardrail**; every path ends with a typed status |
| Persona | **Native-German voice** + warm compliant opener; A/B 2 voices vs simulator |
| Output | **Fixed JSON schema + plain-German note (+ short EN gloss)** |
| Demo | **Minimal web dashboard** (case list → start call → live transcript → result/note/trigger) |
| Stack | **Python + FastAPI** backend; tiny static/React dashboard |

## Non-negotiable compliance rules (cannot break)

These are hard constraints from the brief — enforced in **both the prompt and the code**, and
asserted in tests:

1. **AI-disclosure as the literal first words to a person (EU AI Act).** The agent's very first
   utterance to any human must declare it is an AI — e.g. *"Guten Tag, hier spricht ein
   KI-Assistent im Auftrag des Stromlieferanten Nomos…"*. Disclosure happens **only after the IVR
   is passed and a human is on the line** (not to the menu), and **before** stating the case.
   Enforcement: pinned as the mandatory opening turn in the prompt; a simulator/transcript
   assertion fails the run if the first human-directed utterance is not the disclosure.
2. **Synthetic data only, practice number only.** Every name/ID/address comes solely from
   `fixtures.json`; the agent never invents or uses real customer data, and the system **only ever
   dials the configured practice-clerk number** — never a real grid operator. Enforcement: the
   dial target is a single configured constant the call-init path validates against; any other
   number is refused in code. Combined with the **never-fabricate** guardrail (agent says "I don't
   have that" rather than inventing).

## Architecture

```
[Dashboard] --start case--> [FastAPI orchestrator]
                                  |  initiate outbound call (Twilio), pass case as EL dynamic variables
                                  v
                            [Twilio] --detect IVR, send DTMF '1'--> bridge --> [ElevenLabs Conv AI agent]
                                                                                   |  (German conversation)
                                  live server-tools (HTTPS) <----------------------+  record_finding / validate_id / handoff
                                  |
                            EL post-call webhook --> [extract -> JSON schema -> German note -> trigger mock services]
                                  |
                            [store] --> dashboard shows result + note + triggered action
                            [mock email-agent], [mock sign-up step] endpoints log the triggered action
```

## Components to build

### 1. Backend (FastAPI) — `app/`
- **Call init** (`POST /calls`): take a `case_id`, load from `fixtures.json`, build **dynamic
  variables** including **pre-spelled digit strings** for `malo_id` (and any number the agent must
  speak), then start the outbound call.
- **Twilio call-control / IVR** webhook: on answer, detect menu and **send DTMF `1`** (Lieferantenwechsel),
  then connect the ElevenLabs agent stream once a human is on the line.
- **Live tool endpoints** (called by EL mid-call), all fast/idempotent:
  - `record_finding` / `update_case` — write diagnosis/corrected MaLo/Vorgangsnummer/meter status as confirmed.
  - `validate_id` — **local** checksum/format check for MaLo (11-digit + check digit) & Vorgangsnummer;
    returns the **pre-spelled digit-token** form for clean readback.
  - `end_call` / `handoff_trigger` — signal completion + intended next action.
  - `get_case_context` — safety-net only.
- **Post-call webhook**: receive EL transcript + collected data → normalize into the **fixed JSON
  schema** → generate **plain-German back-office note (+EN gloss)** → **trigger mock services**.
- **Mock services**: `mock_email_agent` (logs queued customer outreach, CASE-A), `mock_signup_step`
  (logs "sign-up advanced" / writes corrected MaLo, CASE-C/handout).
- **Store**: simple persistence (SQLite or JSON file) keyed by `case_id`/`call_id`.

### 2. ElevenLabs agent config
- **System prompt** encoding the 4-phase flow, AI-disclosure-first, proactive 4-fact offer, the
  **per-scenario fallback playbook**, the **never-fabricate** rule, and **digit-by-digit readback** cadence.
- **Dynamic variables** per call (case facts + pre-spelled digit strings).
- **Tools** wired to the backend endpoints above.
- **Native-German voice** selected by A/B against the simulator; calmer rate.

### 3. Helga clerk simulator — `sim/`
- Per-case persona (seeded from `fixtures.json` + the 3 transcripts) that plays the clerk,
  including the IVR menu and curveballs (off-by-one digit, won't-find-case, transfer, voicemail).
- Lets the full voice loop be exercised repeatedly at ~zero cost.

### 4. Dashboard — `web/`
- List 3 cases → **Start call** → live status + streaming transcript → final **structured JSON**,
  **German note**, and **triggered next-action** badge.

## Data: fixed result schema (per call)
`case_id, status (resolved|partial|needs_human), reason, corrected_malo, vorgangsnummer,
meter_status, next_action, confidence, note_de, note_en_gloss, transcript_ref, started_at, ended_at`

## Build order
1. **Scaffold** FastAPI app, config, `fixtures.json` loader, digit-token formatter, result schema + store.
2. **Clerk simulator** (CASE-A persona) — so everything below is testable without the real number.
3. **ElevenLabs agent** (prompt + dynamic vars + tools) + **Twilio outbound + IVR/DTMF**; get a full
   CASE-A call working agent↔simulator.
4. **Live tools** (`validate_id` local checksum + pre-spell, `record_finding`, `handoff_trigger`).
5. **Post-call pipeline**: schema extraction → German note → **mock triggers** (CASE-A email-agent).
6. **CASE-C** (capture + digit-readback of corrected MaLo; sign-up step trigger), then **CASE-B**
   (Vorgangsnummer capture + "no resubmission needed" confirmation).
7. **Robustness playbook** curveballs via simulator; ensure every path yields a typed status.
8. **Dashboard** wired to live status + artifacts.
9. **Voice A/B** + prosody polish for the first-10-seconds warmth.
10. **Final validation**: a small number of real **practice-clerk** calls across A/C/B.

## Verification
- **Simulator runs** (primary loop): for each case, assert the agent (a) declares AI first to a
  human, (b) navigates IVR, (c) offers the 4 facts, (d) reads every ID back digit-by-digit, (e)
  captures the correct outcome, (f) produces schema + German note + correct trigger. Run curveball
  personas and assert graceful `partial`/`needs_human` with no fabricated data.
- **Digit-reading check**: unit-test the digit-token formatter; verify in audio that the 11-digit
  MaLo is spoken digit-by-digit in German (not compressed).
- **Close-the-loop check**: confirm CASE-A triggers the mock email-agent and CASE-C writes the
  corrected MaLo + emits "sign-up advanced"; both visible on the dashboard.
- **Final live**: limited calls to the **practice clerk number only** (never a real operator),
  confirming end-to-end behavior and warmth.

## Risks / watch-items
- **Mid-call tool latency** (thick-orchestrator choice): keep `validate_id` local, prefer dynamic
  variables over `get_case_context`, keep tool responses tiny — pauses are what make Helga hang up.
- **EL DTMF reliability**: mitigated by handling IVR in the Twilio layer instead.
- **STT of spoken digits** (CASE-C capture): mitigated by mandatory digit-by-digit readback-to-confirm.
- **Compliance**: AI-disclosure as literal first words to a human; synthetic data + practice number
  only — enforce both in prompt and in code (never dial anything but the configured practice number).