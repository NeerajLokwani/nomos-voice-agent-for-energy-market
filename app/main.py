"""FastAPI entrypoint für Dashboard, Telefonie-Webhooks und Abschluss-Pipeline."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel

from .config import get_settings
from .finalize import finalize_call
from .fixtures import build_dynamic_variables, get_case, list_cases
from .store import append_transcript, get_live, list_results, set_live
from pathlib import Path

from fastapi.responses import FileResponse

from .telephony import build_call_twiml, place_call
from .tools_routes import router as tools_router
from .triggers import list_triggers

app = FastAPI(title="Nomos Clearing-Calls Voice Agent")
app.include_router(tools_router)

_WEB_DIR = Path(__file__).resolve().parent.parent / "web"


@app.get("/")
def dashboard() -> FileResponse:
    return FileResponse(_WEB_DIR / "index.html")


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

    try:
        sid = place_call(call_id, ivr_digit=req.ivr_digit)
    except ValueError as exc:  # compliance gate / missing config
        set_live(call_id, status="refused", error=str(exc))
        raise HTTPException(status_code=400, detail=str(exc))
    set_live(call_id, status="dialing", twilio_sid=sid)
    return {"call_id": call_id, "status": "dialing", "twilio_sid": sid}


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
    """ElevenLabs post-call webhook. We finalize from our own accumulated state; the
    call_id arrives via the dynamic variables we set at call start."""
    body = await request.json()
    data = body.get("data", body)
    dyn = (
        data.get("conversation_initiation_client_data", {})
        .get("dynamic_variables", {})
    )
    call_id = dyn.get("call_id") or data.get("call_id")
    if not call_id or get_live(call_id) is None:
        raise HTTPException(status_code=404, detail="unknown or missing call_id")
    # capture transcript if present
    for turn in data.get("transcript", []) or []:
        role = turn.get("role", "")
        text = turn.get("message") or turn.get("text") or ""
        if text:
            append_transcript(call_id, role, text)
    result = finalize_call(call_id)
    return {"ok": True, "result": json.loads(result.model_dump_json())}


@app.get("/calls/{call_id}/live")
def call_live(call_id: str) -> dict:
    live = get_live(call_id)
    if live is None:
        raise HTTPException(status_code=404, detail="unknown call")
    return live
