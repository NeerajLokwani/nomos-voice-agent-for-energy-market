from app.fixtures import get_case
from app.reconcile import reconcile
from app.schema import CallResult, CallStatus, MeterStatus, NextAction


def _item(report, field):
    return next(item for item in report.items if item.field == field)


def test_case_a_removed_mit_contact_customer_ist_abweichung():
    case = get_case("CASE-A")
    result = CallResult(
        case_id="CASE-A",
        status=CallStatus.resolved,
        reason="Baustromzähler am 18.05. ausgebaut, alte MaLo tot",
        meter_status=MeterStatus.removed,
        next_action=NextAction.contact_customer,
        confidence=0.9,
    )

    report = reconcile(case, result)

    assert report.verification_status == "abweichung"
    assert _item(report, "meter_status").kind == "verifiziert"
    assert _item(report, "next_action").kind == "abweichung"
    assert _item(report, "next_action").old == "create_new_anlage"
    assert _item(report, "next_action").new == "contact_customer"


def test_case_c_plausible_corrected_malo_ist_geaendert():
    case = get_case("CASE-C")
    result = CallResult(
        case_id="CASE-C",
        status=CallStatus.resolved,
        reason="Zählernummer passt zu einer korrigierten MaLo",
        corrected_malo="71005523911",
        next_action=NextAction.trigger_signup_step,
        confidence=0.9,
    )

    report = reconcile(case, result)

    assert report.verification_status == "verifiziert"
    assert _item(report, "malo_id<->corrected_malo").kind == "geaendert"
    assert _item(report, "corrected_malo_format").kind == "verifiziert"
    assert _item(report, "next_action").kind == "verifiziert"


def test_case_c_corrected_malo_ohne_bekannte_malo_ist_neu():
    case = {**get_case("CASE-C"), "malo_id": ""}
    result = CallResult(
        case_id="CASE-C",
        status=CallStatus.resolved,
        reason="Zählernummer passt zu einer korrigierten MaLo",
        corrected_malo="71005523911",
        next_action=NextAction.trigger_signup_step,
        confidence=0.9,
    )

    report = reconcile(case, result)

    assert report.verification_status == "verifiziert"
    assert _item(report, "malo_id<->corrected_malo").kind == "neu"


def test_case_b_vorgangsnummer_und_keine_neueinreichung_ist_verifiziert():
    case = get_case("CASE-B")
    result = CallResult(
        case_id="CASE-B",
        status=CallStatus.resolved,
        reason="Anmeldung lag korrekt vor, keine Neueinreichung nötig, wird bearbeitet",
        vorgangsnummer="KL202644817",
        next_action=NextAction.await_processing,
        confidence=0.9,
    )

    report = reconcile(case, result)

    assert report.verification_status == "verifiziert"
    assert _item(report, "vorgangsnummer").kind == "neu"
    assert _item(report, "vorgangsnummer_format").kind == "verifiziert"
    assert _item(report, "next_action").kind == "verifiziert"


def test_ungueltige_malo_markiert_mensch_noetig():
    case = get_case("CASE-C")
    result = CallResult(
        case_id="CASE-C",
        status=CallStatus.resolved,
        reason="Sachbearbeiter nannte eine MaLo, Format ist aber ungültig",
        corrected_malo="123",
        next_action=NextAction.trigger_signup_step,
        confidence=0.6,
    )

    report = reconcile(case, result)

    assert report.verification_status == "mensch_noetig"
    assert _item(report, "corrected_malo_format").kind == "ungueltig"
    assert "Manuelle Prüfung nötig." in report.summary_points


def test_fehlende_felder_bleiben_offen_und_werden_nicht_erfunden():
    case = get_case("CASE-A")
    result = CallResult(
        case_id="CASE-A",
        status=CallStatus.partial,
        reason="",
        meter_status=MeterStatus.unknown,
        next_action=NextAction.none,
        confidence=0.2,
    )

    report = reconcile(case, result)

    assert _item(report, "malo_id<->corrected_malo").new == ""
    assert _item(report, "malo_id<->corrected_malo").kind == "offen"
    assert _item(report, "vorgangsnummer").new == ""
    assert _item(report, "vorgangsnummer").kind == "offen"
    assert _item(report, "anmeldung_datum").new == ""
    assert _item(report, "lieferbeginn").new == ""
