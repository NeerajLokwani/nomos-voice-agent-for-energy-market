from app.fixtures import get_case
from sim.personas import CURVEBALLS, PERSONAS, render_clerk_prompt


def test_all_fixture_cases_have_a_persona():
    for cid in ("CASE-A", "CASE-B", "CASE-C"):
        assert cid in PERSONAS


def test_case_c_uses_digit_2_not_1():
    # The Marktkommunikation menu routes via 2, the trap most agents miss.
    assert PERSONAS["CASE-C"].ivr_digit == "2"
    assert PERSONAS["CASE-A"].ivr_digit == "1"
    assert PERSONAS["CASE-B"].ivr_digit == "1"


def test_case_c_corrected_malo_differs_from_held_malo():
    held = get_case("CASE-C")["malo_id"]
    corrected = PERSONAS["CASE-C"].corrected_malo
    assert corrected and corrected != held  # the whole point of CASE-C


def test_case_b_has_vorgangsnummer():
    assert PERSONAS["CASE-B"].vorgangsnummer


def test_render_prompt_contains_menu_and_digit():
    prompt = render_clerk_prompt("CASE-C", "happy")
    assert "drücken Sie die 2" in prompt
    assert "Petra Brandt" in prompt
    assert "71005523911" in prompt  # corrected MaLo injected


def test_all_curveball_variants_render():
    for variant in CURVEBALLS:
        for cid in PERSONAS:
            assert render_clerk_prompt(cid, variant)
