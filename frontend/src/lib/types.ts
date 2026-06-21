// Shared types mirroring the FastAPI backend (app/schema.py, app/fixtures.py).
// Keep these in sync with the Python models so the contract is explicit.

export type CallStatus = "resolved" | "partial" | "needs_human";
export type MeterStatus = "active" | "removed" | "unknown";
export type NextAction =
  | "none"
  | "trigger_signup_step"
  | "contact_customer"
  | "create_new_anlage"
  | "await_processing"
  | "needs_human_followup";

/** Summary shown in the case queue (GET /cases). */
export interface CaseSummary {
  id: string;
  case_title: string;
  vnb_name: string;
  lieferstelle: string;
  symptom: string;
  goal: string;
}

/** Per-call dynamic variables incl. pre-spelled digit tokens (GET /cases/{id}/variables). */
export interface CaseVariables {
  case_id: string;
  case_title: string;
  lieferant: string;
  vnb_name: string;
  lieferstelle: string;
  zaehlernummer: string;
  malo_id: string;
  malo_id_spoken: string;
  zaehlernummer_spoken: string;
  anmeldung_datum: string;
  anmeldung_datum_spoken: string;
  lieferbeginn: string;
  lieferbeginn_spoken: string;
  statustext: string;
  symptom: string;
  goal: string;
}

/** Structured outcome (POST /calls/{id}/finalize, app/schema.py CallResult). */
export interface CallResult {
  case_id: string;
  call_id: string | null;
  status: CallStatus;
  reason: string;
  corrected_malo: string | null;
  vorgangsnummer: string | null;
  meter_status: MeterStatus;
  next_action: NextAction;
  confidence: number;
  note_de: string;
  note_en_gloss: string;
  transcript_ref: string | null;
  triggered: string[];
  started_at: string | null;
  ended_at: string | null;
}

export interface TranscriptTurn {
  role: string;
  text: string;
}

/** Server-side live snapshot (GET /calls/{id}/live). */
export interface LiveSnapshot {
  call_id: string;
  case_id?: string;
  status?: string;
  transcript?: TranscriptTurn[];
}

/** Client-side UI state for the live-call panel. */
export interface LiveState {
  on: boolean;
  meta: string;
  transcript: TranscriptTurn[];
  note?: string | null;
  placeholder?: string;
}

export type StartCallResponse =
  | { call_id: string; status: string; dynamic_variables?: CaseVariables }
  | { error: string };

export interface DigitTile {
  ch: string;
  alpha: boolean;
}

// --- Close-the-loop pipeline (post-call webhook → grounded facts → note → triggers) ---

export interface CLTranscriptTurn {
  role: "agent" | "user";
  message: string;
}

export interface ExtractedFacts {
  malo_id: string | null;
  stuck_reason: string | null;
  next_step: string | null;
  ticket_number: string | null;
  vorgang_nr: string | null;
  needs_human: boolean;
  analysis_confidence: number;
  grounding_notes: string[];
  source: string;
}

export interface EmailDraft {
  subject: string;
  body: string;
  needs_human: boolean;
}

export interface TriggeredAction {
  type: string;
  status: "fired" | "skipped" | "flagged";
  detail: string;
  target: string | null;
  fired_at: string;
}

export interface ConversationRecord {
  conversation_id: string;
  call_id: string | null;
  agent_id: string | null;
  case: string | null;
  transcript: CLTranscriptTurn[];
  facts: ExtractedFacts;
  note: string;
  email_draft: EmailDraft;
  actions: TriggeredAction[];
  received_at: string;
}
