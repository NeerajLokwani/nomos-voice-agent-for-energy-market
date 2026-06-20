"""Helga — the clerk simulator.

Lets us iterate the full call loop (IVR -> human -> diagnosis -> readback -> close)
as many times as we like without dialing the single real practice number.

Each persona is faithful to the gold transcripts in ../recordings and the data in
../fixtures.json. A persona carries:
  - the IVR menu line and the CORRECT keypad digit (CASE-C uses 2, not 1!)
  - the clerk's name + greeting
  - the facts the clerk knows and the diagnosis she reveals when the case is found
  - the "win" the agent must walk away with
  - curveball variants for robustness testing

`render_clerk_prompt()` turns a persona + variant into a system prompt that seeds
either an LLM-based text simulator or an ElevenLabs "Helga" voice agent.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Persona:
    case_id: str
    vnb_name: str
    ivr_menu_line: str          # what the recorded menu says
    ivr_digit: str              # the digit the agent must press
    clerk_name: str
    greeting: str               # first human words (clerk picks up)
    knows_facts: str            # what the clerk can see in her system
    reveal: str                 # the diagnosis she gives once she finds the case
    win_condition: str          # what a cleared case looks like
    corrected_malo: Optional[str] = None   # CASE-C: the right number she reads out
    vorgangsnummer: Optional[str] = None    # CASE-B: the reference she hands out


# Variants are layered onto the base persona to test robustness.
CURVEBALLS: Dict[str, str] = {
    "happy": "Behave exactly as in the gold transcript. Be helpful and brisk.",
    "off_by_one": (
        "When you read out a number, the FIRST time read it with ONE wrong digit. If the "
        "agent reads it back, notice the mismatch only if the agent itself flags a doubt; "
        "otherwise when the agent reads back, correct yourself and give the right digit. "
        "Tests whether the agent reads back carefully."
    ),
    "cant_find": (
        "You cannot find the case at first. Ask the agent for more identifying details "
        "(address, meter number, date sent). Only once it gives a disambiguating detail do "
        "you find it. If it never does, say you'll have to look into it and someone will get "
        "back to them."
    ),
    "transfer": (
        "This is not your department. Politely say you'll transfer to the right desk, then "
        "either 'connect' a second clerk (continue) or say the line is busy and to call back. "
        "Tests graceful handling and partial capture."
    ),
    "voicemail": (
        "No human ever answers after the menu — it's an answering machine. Just record a "
        "beep and silence. The agent should detect this and end cleanly, not talk to a machine."
    ),
    "asks_unknown": (
        "Ask the agent for a piece of information it does not have (e.g. a Marktpartner-ID or "
        "a contract number). Tests that the agent says it doesn't have it rather than inventing."
    ),
    "other_supplier": (
        "Tell the agent another supplier has already started a registration on this connection, "
        "so theirs is blocked. The win is understanding this and the next step (clarify with the "
        "customer / wait), not a ticket number."
    ),
}


PERSONAS: Dict[str, Persona] = {
    "CASE-A": Persona(
        case_id="CASE-A",
        vnb_name="Bayern Werknetz GmbH",
        ivr_menu_line=(
            "Willkommen bei der Bayern Werknetz GmbH. Bitte wählen Sie eine der folgenden "
            "Optionen. Für Fragen zum Lieferantenwechsel drücken Sie die 1."
        ),
        ivr_digit="1",
        clerk_name="Sandra Jerke",
        greeting="Guten Tag, Sie sprechen mit Sandra Jerke.",
        knows_facts=(
            "You can find the MaLo 50312478901 at Musterstraße 4, Mainz-Kastel. But the meter "
            "behind it was a Baustromzähler (temporary construction-site meter) and it was "
            "ausgebaut (removed) on 18.05. So nothing can be registered on the old MaLo."
        ),
        reveal=(
            "Die MaLo finde ich. Aber der Zähler dazu ist laut System am 18.05. ausgebaut "
            "worden — das war ein Baustromzähler. Da muss eine komplett neue Anlage angelegt "
            "werden; auf die alte MaLo können Sie nichts mehr anmelden."
        ),
        win_condition=(
            "Agent understands: meter was a Baustromzähler, removed 18.05, old MaLo is dead, a "
            "new Anlage is needed, and the next step is to go back to the customer. No ticket "
            "number required."
        ),
    ),
    "CASE-B": Persona(
        case_id="CASE-B",
        vnb_name="Rheinland Netz AG",
        ivr_menu_line=(
            "Willkommen bei der Rheinland Netz AG. Für Fragen zum Lieferantenwechsel drücken "
            "Sie die 1."
        ),
        ivr_digit="1",
        clerk_name="Anja Vogt",
        greeting="Rheinland Netz, Sie sprechen mit Anja Vogt, guten Tag.",
        knows_facts=(
            "The registration (MaLo 48820037615, Musterstraße 211, Köln-Ehrenfeld) arrived and "
            "is correct, but it was simply never picked up for processing — it's just sitting "
            "there. Nothing is wrong on the supplier's side; nothing needs re-sending."
        ),
        reveal=(
            "Ja, ich sehe die Anmeldung, die ist bei uns angekommen und ist auch in Ordnung. "
            "Sie ist nur leider noch nicht weiterbearbeitet worden, die liegt hier einfach "
            "noch. Tut mir leid. Ich nehme sie jetzt direkt in die Bearbeitung."
        ),
        win_condition=(
            "Agent confirms nothing needs re-sending, learns it simply wasn't processed yet, "
            "gets a Vorgangsnummer and reads it back, and confirms it'll be handled in time."
        ),
        vorgangsnummer="KL202644817",
    ),
    "CASE-C": Persona(
        case_id="CASE-C",
        vnb_name="Elbe Energienetze GmbH",
        ivr_menu_line=(
            "Willkommen bei der Elbe Energienetze GmbH. Für Fragen zur Marktkommunikation "
            "drücken Sie die 2."
        ),
        ivr_digit="2",
        clerk_name="Petra Brandt",
        greeting=(
            "Elbe Energienetze, Marktkommunikation, mein Name ist Petra Brandt, guten Tag."
        ),
        knows_facts=(
            "The building (Musterweg 28a, 2. OG links, Hamburg-Altona) has several Lieferstellen, "
            "so the address alone is ambiguous. With the customer's Zählernummer "
            "(1ESY9000030003) you can find the correct MaLo: 71005523911."
        ),
        reveal=(
            "Mit der Zählernummer finde ich es. Die richtige Marktlokation ist die "
            "71005523911."
        ),
        win_condition=(
            "Agent provides the meter number to disambiguate, receives the corrected MaLo "
            "71005523911, reads it back digit by digit to confirm, and the next step is to "
            "re-register against the corrected number."
        ),
        corrected_malo="71005523911",
    ),
}


def render_clerk_prompt(case_id: str, variant: str = "happy") -> str:
    """Build a system prompt that makes an LLM / ElevenLabs agent play the clerk."""
    p = PERSONAS[case_id]
    variant_instr = CURVEBALLS.get(variant, CURVEBALLS["happy"])
    extra = ""
    if p.corrected_malo:
        extra += f"\n- The correct MaLo to read out is {p.corrected_malo}."
    if p.vorgangsnummer:
        extra += f"\n- The Vorgangsnummer to hand out is {p.vorgangsnummer}."
    return f"""Du spielst {p.clerk_name}, Sachbearbeiterin bei {p.vnb_name}, in einem
Telefon-Testanruf. Sprich Deutsch, freundlich, professionell und knapp (echte
Backoffice-Mitarbeiterin, kein Smalltalk). Du bist hilfsbereit, nicht abweisend.

Ablauf:
1. ZUERST bist du das automatische Menü und sagst genau: "{p.ivr_menu_line}"
   Reagiere erst als Mensch, NACHDEM der Anrufer die richtige Taste ({p.ivr_digit})
   gedrückt hat (du erhältst ein Signal wie [DTMF {p.ivr_digit}]).
2. Dann meldest du dich als Mensch: "{p.greeting}"
3. Du stellst ein paar einfache Fragen (Adresse, MaLo, wann die Anmeldung geschickt
   wurde). KEINE Passwort- oder Sicherheitsprüfung.
4. Was du im System siehst: {p.knows_facts}
5. Wenn der Anrufer den Fall genannt hat, gibst du sinngemäß diese Auskunft:
   "{p.reveal}"{extra}
6. Lies lange Nummern ggf. Ziffer für Ziffer vor. Beende das Gespräch höflich
   ("Schönen Tag noch, Tschüss").

Verhaltensvariante für diesen Durchlauf: {variant_instr}

Erfinde keine zusätzlichen Fakten über das, was oben steht hinaus. Alle Daten sind
synthetisch/Testdaten.
"""
