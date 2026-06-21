"""Mailversand für Backoffice-Zusammenfassungen."""
from __future__ import annotations

import re
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path
from typing import Optional

import httpx

from .config import get_settings
from .triggers import _emit

RESEND_ENDPOINT = "https://api.resend.com/emails"


def send_summary_email(
    subject: str,
    body_text: str,
    body_html: Optional[str] = None,
    to: Optional[str] = None,
) -> str:
    """Sende oder mocke eine Backoffice-Mail und gib die Mail-Referenz zurück."""
    settings = get_settings()
    mode = (settings.email_mode or "mock").lower()
    recipient = to or settings.email_to_nomos
    if mode == "resend":
        return _send_resend(settings, subject, body_text, body_html, recipient)
    if mode == "smtp":
        return _send_smtp(settings, subject, body_text, body_html, recipient)
    return _send_mock(settings, subject, body_text, body_html, recipient)


def _send_resend(settings, subject: str, body_text: str, body_html: Optional[str], to: str) -> str:
    if not settings.resend_api_key:
        raise ValueError("RESEND_API_KEY fehlt für EMAIL_MODE=resend.")
    if not settings.email_from:
        raise ValueError("EMAIL_FROM fehlt für EMAIL_MODE=resend.")
    if not to:
        raise ValueError("EMAIL_TO_NOMOS oder to fehlt für EMAIL_MODE=resend.")

    payload = {
        "from": settings.email_from,
        "to": [to],
        "subject": subject,
        "text": body_text,
        "html": body_html or _plain_text_html(body_text),
    }
    response = httpx.post(
        RESEND_ENDPOINT,
        headers={"Authorization": f"Bearer {settings.resend_api_key}"},
        json=payload,
        timeout=10.0,
    )
    response.raise_for_status()
    data = response.json()
    mail_id = data.get("id")
    if not mail_id:
        raise ValueError("Resend-Antwort enthält keine id.")
    return str(mail_id)


def _send_smtp(settings, subject: str, body_text: str, body_html: Optional[str], to: str) -> str:
    if not settings.smtp_user or not settings.smtp_password:
        raise ValueError("SMTP_USER oder SMTP_PASSWORD fehlt für EMAIL_MODE=smtp.")
    if not to:
        raise ValueError("EMAIL_TO_NOMOS fehlt für EMAIL_MODE=smtp.")

    msg = EmailMessage()
    msg["From"] = settings.smtp_user
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body_text)
    if body_html:
        msg.add_alternative(body_html, subtype="html")

    context = ssl.create_default_context()
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.ehlo()
        server.starttls(context=context)
        server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)

    return f"smtp-{settings.smtp_user}->{to}"


def _send_mock(
    settings,
    subject: str,
    body_text: str,
    body_html: Optional[str],
    to: Optional[str],
) -> str:
    case_id = _extract_case_id(subject, body_text)
    mail_id = f"mock-{case_id}"
    outbox = Path("outbox")
    outbox.mkdir(parents=True, exist_ok=True)
    html_body = body_html or _plain_text_html(body_text)

    message = EmailMessage()
    message["From"] = settings.email_from
    message["To"] = to or settings.email_to_test or settings.email_to_nomos or "mock@nomos.local"
    message["Subject"] = subject
    message.set_content(body_text)
    message.add_alternative(html_body, subtype="html")

    (outbox / f"{case_id}.eml").write_text(message.as_string(), encoding="utf-8")
    (outbox / f"{case_id}.html").write_text(html_body, encoding="utf-8")
    _emit(
        "email_agent",
        {
            "id": mail_id,
            "mode": "mock",
            "case_id": case_id,
            "to": message["To"],
            "subject": subject,
            "eml": str(outbox / f"{case_id}.eml"),
            "html": str(outbox / f"{case_id}.html"),
        },
    )
    return mail_id


def _extract_case_id(subject: str, body_text: str) -> str:
    match = re.search(r"\bCASE-[A-Za-z0-9_-]+\b", f"{subject}\n{body_text}")
    if match:
        return match.group(0)
    slug = re.sub(r"[^A-Za-z0-9_-]+", "-", subject).strip("-")
    return slug[:60] or "unknown"


def _plain_text_html(body_text: str) -> str:
    import html

    escaped = html.escape(body_text)
    return "<p>" + escaped.replace("\n\n", "</p><p>").replace("\n", "<br>") + "</p>"
