"""CLI zum Nachverifizieren eines Falls und Versenden der Follow-up-Mail."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

from .config import get_settings
from .email_agent import send_summary_email
from .fixtures import get_case
from .reconcile import reconcile
from .schema import CallResult
from .store import get_result, list_results
from .summary import build_email_summary

SYNTHETIC_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures"


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Verifiziere einen Nomos-Fall und sende eine Mail.")
    parser.add_argument("case_id", help="Fall-ID, z.B. CASE-A")
    parser.add_argument("--from-file", dest="from_file", help="JSON-Datei mit eingehenden CallResult-Daten")
    args = parser.parse_args(argv)

    case = get_case(args.case_id)
    if not case:
        print(f"Unbekannter Fall: {args.case_id}")
        return 1

    result = _load_call_result(args.case_id, args.from_file)
    report = reconcile(case, result)
    summary = build_email_summary(case, result, report)
    to = get_settings().email_to_test if args.from_file else None
    mail_ref = send_summary_email(
        summary["subject"],
        summary["body_text"],
        summary.get("body_html"),
        to=to or None,
    )

    print("ReconciliationReport:")
    print(json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2))
    print(f"Mail-Referenz: {mail_ref}")
    print(f"Mail-Pfad: {_mail_path(args.case_id, mail_ref)}")
    return 0


def _load_call_result(case_id: str, from_file: Optional[str]) -> CallResult:
    if from_file:
        return _load_from_file(Path(from_file), case_id)

    stored = _stored_result(case_id)
    if stored:
        return CallResult.model_validate(stored)

    return _load_from_file(SYNTHETIC_DIR / f"callresult_{case_id}.json", case_id)


def _stored_result(case_id: str) -> Optional[dict]:
    direct = get_result(case_id)
    if direct:
        return direct
    matches = [result for result in list_results() if result.get("case_id") == case_id]
    return matches[-1] if matches else None


def _load_from_file(path: Path, case_id: str) -> CallResult:
    data = json.loads(path.read_text(encoding="utf-8"))
    if "case_id" not in data:
        data["case_id"] = case_id
    return CallResult.model_validate(data)


def _mail_path(case_id: str, mail_ref: str) -> str:
    if mail_ref.startswith("mock-"):
        return str(Path("outbox") / f"{case_id}.eml")
    return mail_ref


if __name__ == "__main__":
    raise SystemExit(main())
