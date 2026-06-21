// Thin wrapper over the FastAPI orchestrator. Same-origin in prod (FastAPI serves
// the build); proxied to :8000 in dev via vite.config.ts.
import type {
  CallResult,
  CaseSummary,
  CaseVariables,
  ConversationRecord,
  LiveSnapshot,
  StartCallResponse,
} from "./types";

async function jsonOrError<T>(res: Response): Promise<T | { error: string }> {
  const body = await res.json().catch(() => ({}));
  if (body && typeof body === "object" && "detail" in body) {
    return { error: String((body as { detail: unknown }).detail) };
  }
  return body as T;
}

export const api = {
  listCases: (): Promise<CaseSummary[]> => fetch("/cases").then((r) => r.json()),

  caseVariables: (id: string): Promise<CaseVariables> =>
    fetch(`/cases/${id}/variables`).then((r) => r.json()),

  startCall: (caseId: string, dryRun: boolean): Promise<StartCallResponse> =>
    fetch("/calls", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ case_id: caseId, dry_run: dryRun }),
    }).then((r) => jsonOrError(r)),

  live: (callId: string): Promise<LiveSnapshot> =>
    fetch(`/calls/${callId}/live`).then((r) => r.json()),

  finalize: (callId: string): Promise<CallResult | { error: string }> =>
    fetch(`/calls/${callId}/finalize`, { method: "POST" }).then((r) =>
      jsonOrError<CallResult>(r)
    ),

  // --- close-the-loop: post-call extraction record ---
  conversation: (key: string): Promise<ConversationRecord | { error: string }> =>
    fetch(`/api/conversations/${key}`).then((r) => jsonOrError<ConversationRecord>(r)),

  simulatePostcall: (caseId: string): Promise<ConversationRecord | { error: string }> =>
    fetch(`/api/simulate-postcall/${caseId}`, { method: "POST" }).then((r) =>
      jsonOrError<ConversationRecord>(r)
    ),
};
