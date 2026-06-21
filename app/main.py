"""FastAPI entrypoint.

Scaffold stage: health + case listing + dynamic-variable preview. Call init,
Twilio/IVR webhooks, live tools, and the post-call pipeline are added in later steps.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel

from .closeloop.pipeline import process_call
from .closeloop.schema import WebhookPayload
from .closeloop.webhook import normalize_payload, verify_signature
from .config import get_settings
from .finalize import finalize_call
from .fixtures import build_dynamic_variables, get_case, list_cases
from .store import (
    append_transcript,
    get_conversation,
    get_live,
    list_conversations,
    list_results,
    save_conversation,
    set_live,
)
from pathlib import Path

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .elevenlabs_client import place_call_via_elevenlabs
from .telephony import build_call_twiml, place_call
from .tools_routes import router as tools_router
from .triggers import list_triggers

app = FastAPI(title="Nomos Clearing-Calls Voice Agent")
app.include_router(tools_router)

_ROOT = Path(__file__).resolve().parent.parent
_REACT_DIST = _ROOT / "frontend" / "dist"   # built React app (npm run build)
_LEGACY_WEB = _ROOT / "web"                  # fallback single-file dashboard

# Serve the React build's hashed assets when present.
if (_REACT_DIST / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=_REACT_DIST / "assets"), name="assets")


def _load_sample_payloads() -> dict:
    with open(_ROOT / "app" / "closeloop" / "sample_payloads.json", encoding="utf-8") as fh:
        return json.load(fh)


@app.get("/")
def dashboard() -> FileResponse:
    """Serve the React dashboard if built, else the legacy single-file dashboard."""
    react_index = _REACT_DIST / "index.html"
    if react_index.is_file():
        return FileResponse(react_index)
    return FileResponse(_LEGACY_WEB / "index.html")


class StartCallRequest(BaseModel):
    case_id: str
    # Optional override of the menu digit; used when pointing at the Helga simulator
    # (e.g. "2" for CASE-C). For the real practice line, leave unset.
    ivr_digit: Optional[str] = None
    # If true, prepare the call (dynamic vars + TwiML) without actually dialing Twilio.
    # Handy for local demos before creds/practice number are wired up.
    dry_run: bool = False


@app.get("/health")
def health() -> dict:
    s = get_settings()
    return {
        "ok": True,
        "practice_number_configured": bool(s.practice_clerk_number),
        "twilio_configured": bool(s.twilio_account_sid and s.twilio_from_number),
        "elevenlabs_configured": bool(s.elevenlabs_api_key and s.elevenlabs_agent_id),
    }


@app.get("/cases")
def cases() -> list:
    """Summary list for the dashboard."""
    return [
        {
            "id": c.get("id"),
            "case_title": c.get("case_title"),
            "vnb_name": c.get("vnb_name"),
            "lieferstelle": c.get("lieferstelle"),
            "symptom": c.get("symptom"),
            "goal": c.get("goal"),
        }
        for c in list_cases()
    ]


@app.get("/cases/{case_id}/variables")
def case_variables(case_id: str) -> dict:
    """Preview the dynamic variables (incl. pre-spelled digit tokens) for a case."""
    case = get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="unknown case")
    return build_dynamic_variables(case)


@app.get("/results")
def results() -> list:
    return list_results()


@app.get("/triggers")
def triggers() -> list:
    return list_triggers()


@app.post("/calls")
def start_call(req: StartCallRequest) -> dict:
    """Prepare and (unless dry_run) place an outbound clearing call for a case."""
    case = get_case(req.case_id)
    if not case:
        raise HTTPException(status_code=404, detail="unknown case")

    call_id = uuid.uuid4().hex
    dynamic_variables = build_dynamic_variables(case)
    set_live(
        call_id,
        case_id=req.case_id,
        status="preparing",
        ivr_digit=req.ivr_digit,
        dynamic_variables=dynamic_variables,
        started_at=datetime.now(timezone.utc).isoformat(),
    )

    if req.dry_run:
        set_live(call_id, status="dry_run")
        return {"call_id": call_id, "status": "dry_run", "dynamic_variables": dynamic_variables}

    # Native ElevenLabs outbound: EL owns the Twilio call + media bridge, and the agent
    # navigates the IVR itself via its play_keypad_touch_tone tool. We pass call_id in the
    # dynamic variables so the live tools + post-call webhook can tie back to this case.
    s = get_settings()
    try:
        result = place_call_via_elevenlabs(
            s.practice_clerk_number,
            {**dynamic_variables, "call_id": call_id},
        )
    except ValueError as exc:  # compliance gate / missing config
        set_live(call_id, status="refused", error=str(exc))
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # EL API error
        set_live(call_id, status="error", error=str(exc))
        raise HTTPException(status_code=502, detail=f"ElevenLabs outbound failed: {exc}")
    set_live(call_id, status="dialing", el_response=result)
    return {"call_id": call_id, "status": "dialing", "elevenlabs": result}


@app.api_route("/voice/{call_id}", methods=["GET", "POST"])
def voice_twiml(call_id: str, ivr_digit: Optional[str] = None) -> Response:
    """TwiML Twilio fetches when the call connects: navigate IVR, bridge to EL agent."""
    live = get_live(call_id)
    if not live:
        raise HTTPException(status_code=404, detail="unknown call")
    twiml = build_call_twiml(
        call_id,
        live.get("dynamic_variables", {}),
        ivr_digit=ivr_digit or live.get("ivr_digit"),
    )
    return Response(content=twiml, media_type="application/xml")


@app.post("/twilio/status/{call_id}")
async def twilio_status(call_id: str, request: Request) -> dict:
    form = await request.form()
    set_live(call_id, status=f"twilio:{form.get('CallStatus', 'unknown')}")
    return {"ok": True}


@app.post("/calls/{call_id}/finalize")
def finalize(call_id: str) -> dict:
    """Build the structured result, write the note, fire mock triggers."""
    try:
        result = finalize_call(call_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="unknown call")
    return json.loads(result.model_dump_json())


@app.post("/elevenlabs/post-call")
async def elevenlabs_post_call(request: Request) -> dict:
    """ElevenLabs post-call webhook — the real close-the-loop entry point.

    Normalizes the EL envelope (transcript + data_collection_results), grounds the
    facts against the transcript (never-fabricate), builds the German note + email
    draft, fires triggers, and stores a ConversationRecord keyed by our call_id.
    """
    raw = await request.body()
    ok, reason = verify_signature(raw, request.headers.get("ElevenLabs-Signature"))
    if not ok:
        raise HTTPException(status_code=401, detail=f"Signature check failed: {reason}")
    try:
        body = json.loads(raw)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    try:
        payload = WebhookPayload.model_validate(normalize_payload(body))
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Bad payload: {exc}")

    record = process_call(payload)
    record_dict = json.loads(record.model_dump_json())
    save_conversation(record_dict)

    # mirror the transcript into the live view if we recognise the call
    if record.call_id and get_live(record.call_id) is not None:
        for turn in record.transcript:
            if turn.message:
                append_transcript(record.call_id, turn.role, turn.message)
        set_live(record.call_id, status="ended")
    return {"ok": True, "record": record_dict}


@app.get("/api/conversations")
def api_conversations() -> list:
    return list_conversations()


@app.get("/api/conversations/{key}")
def api_conversation(key: str) -> dict:
    rec = get_conversation(key)
    if not rec:
        raise HTTPException(status_code=404, detail="unknown conversation")
    return rec


@app.post("/api/simulate-postcall/{case}")
def api_simulate_postcall(case: str) -> dict:
    """Run a sample ElevenLabs post-call payload through the real pipeline and store
    the record — lets the dashboard demo the close-the-loop without a live call."""
    samples = _load_sample_payloads()
    if case not in samples or case.startswith("_"):
        raise HTTPException(status_code=404, detail=f"unknown sample case: {case}")
    payload = WebhookPayload.model_validate(samples[case]["payload"])
    record = process_call(payload)
    record_dict = json.loads(record.model_dump_json())
    save_conversation(record_dict)
    return record_dict


@app.get("/calls/{call_id}/live")
def call_live(call_id: str) -> dict:
    live = get_live(call_id)
    if live is None:
        raise HTTPException(status_code=404, detail="unknown call")
    return live
