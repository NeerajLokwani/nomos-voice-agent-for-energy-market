from app.agent_prompt import AGENT_SYSTEM_PROMPT, FIRST_MESSAGE
from app.elevenlabs_client import build_tools_spec


def test_first_message_declares_ai():
    # EU AI Act: the agent's first words to a human must declare it is an AI.
    assert "KI-Assistent" in FIRST_MESSAGE


def test_prompt_encodes_both_hard_rules():
    assert "EU AI Act" in AGENT_SYSTEM_PROMPT
    assert "Erfinde" in AGENT_SYSTEM_PROMPT  # never-fabricate rule
    # reads pre-spelled digit fields, not raw numbers
    assert "{{malo_id_spoken}}" in AGENT_SYSTEM_PROMPT
    # digit-by-digit readback discipline
    assert "Ziffer für Ziffer" in AGENT_SYSTEM_PROMPT


def test_tools_spec_has_the_four_tools():
    names = {t["name"] for t in build_tools_spec("http://x")}
    assert names == {"validate_id", "record_finding", "end_call", "get_case_context"}


def test_tools_point_at_our_endpoints():
    for t in build_tools_spec("http://host"):
        assert t["api_schema"]["url"] == f"http://host/tools/{t['name']}"
        assert t["api_schema"]["method"] == "POST"
