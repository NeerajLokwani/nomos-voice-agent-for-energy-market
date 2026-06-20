"""Run a full text conversation between our agent and the Helga simulator.

This is the unlimited, near-zero-cost dev loop: iterate the conversation logic (German
flow, AI-disclosure-first, digit-by-digit readback, curveball handling) without dialing
the single real practice number.

Requires OPENAI_API_KEY. Both sides are played by an OpenAI chat model:
  - agent: our real AGENT_SYSTEM_PROMPT with the case's dynamic variables substituted
  - clerk: sim.personas.render_clerk_prompt(case, variant)

Usage:
    python -m sim.harness CASE-A happy
    python -m sim.harness CASE-C off_by_one
"""
from __future__ import annotations

import os
import sys
from typing import List

from app.agent_prompt import AGENT_SYSTEM_PROMPT, FIRST_MESSAGE, render
from app.fixtures import build_dynamic_variables, get_case
from .personas import PERSONAS, render_clerk_prompt

MODEL = os.getenv("SIM_MODEL", "gpt-4o")
MAX_TURNS = int(os.getenv("SIM_MAX_TURNS", "16"))


def _client():
    try:
        from openai import OpenAI
    except ImportError:
        sys.exit("pip install openai to run the harness")
    if not os.getenv("OPENAI_API_KEY"):
        sys.exit("set OPENAI_API_KEY to run the harness")
    return OpenAI()


def _say(client, system: str, history: List[dict]) -> str:
    # OpenAI takes the system prompt as the first message in the list.
    messages = [{"role": "system", "content": system}, *history]
    resp = client.chat.completions.create(
        model=MODEL, max_tokens=400, messages=messages
    )
    return (resp.choices[0].message.content or "").strip()


def run(case_id: str, variant: str = "happy", verbose: bool = True) -> List[dict]:
    """Return the transcript as [{speaker, text}, ...]."""
    client = _client()
    case = get_case(case_id)
    dv = build_dynamic_variables(case)
    agent_system = render(AGENT_SYSTEM_PROMPT, dv)
    clerk_system = render_clerk_prompt(case_id, variant)

    transcript: List[dict] = []
    # The clerk opens as the IVR menu.
    clerk_hist: List[dict] = [{"role": "user", "content": "[Anruf verbunden]"}]
    clerk_msg = _say(client, clerk_system, clerk_hist)
    clerk_hist.append({"role": "assistant", "content": clerk_msg})
    transcript.append({"speaker": "clerk", "text": clerk_msg})
    if verbose:
        print(f"[CLERK] {clerk_msg}\n")

    # Our agent navigates the menu deterministically (Twilio layer would send the digit).
    digit = PERSONAS[case_id].ivr_digit
    agent_hist: List[dict] = [
        {"role": "user", "content": f"{clerk_msg}\n[System: Taste {digit} wurde gedrückt.]"}
    ]

    for _ in range(MAX_TURNS):
        agent_msg = _say(client, agent_system, agent_hist)
        agent_hist.append({"role": "assistant", "content": agent_msg})
        transcript.append({"speaker": "agent", "text": agent_msg})
        if verbose:
            print(f"[AGENT] {agent_msg}\n")
        if "tschüss" in agent_msg.lower() or "auf wiederhören" in agent_msg.lower():
            break

        clerk_hist.append({"role": "user", "content": agent_msg})
        clerk_msg = _say(client, clerk_system, clerk_hist)
        clerk_hist.append({"role": "assistant", "content": clerk_msg})
        transcript.append({"speaker": "clerk", "text": clerk_msg})
        if verbose:
            print(f"[CLERK] {clerk_msg}\n")
        agent_hist.append({"role": "user", "content": clerk_msg})

    return transcript


def first_agent_message(case_id: str) -> str:
    """The disclosure opener with variables substituted (no API needed)."""
    return render(FIRST_MESSAGE, build_dynamic_variables(get_case(case_id)))


if __name__ == "__main__":
    cid = sys.argv[1] if len(sys.argv) > 1 else "CASE-A"
    var = sys.argv[2] if len(sys.argv) > 2 else "happy"
    run(cid, var)
