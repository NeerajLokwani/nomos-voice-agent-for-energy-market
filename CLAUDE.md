# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Sprache

Code, Kommentare und Antworten auf **Deutsch**. Variablennamen und Docstrings im Code bleiben Englisch (Projektkonvention).

## Befehle

```bash
# Setup
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# Server
uvicorn app.main:app --reload

# Tests (60 Tests, ~0.3s)
python -m pytest -q

# Einzeltest
python -m pytest tests/test_reconcile.py::test_case_a_removed_mit_contact_customer_ist_abweichung

# Verification-CLI (Mock-Modus, keine Keys nötig)
python -m app.verify CASE-A
python -m app.verify CASE-A --from-file samples/inbound_CASE-A.json

# Simulator (braucht OPENAI_API_KEY)
python -m sim.harness CASE-A
python -m sim.harness CASE-C off_by_one

# Agent-Prompt zu ElevenLabs pushen
python -m scripts.sync_agent
python -m scripts.sync_agent <voice_id>
```

## Architektur

KI-Voice-Agent für den deutschen Energiemarkt (Nomos Hackathon). Ruft Netzbetreiber-Sachbearbeiter an, klärt festgefahrene MaKo-Fälle, erzeugt strukturierte Ergebnisse + deutsche Backoffice-Notiz + löst Folgeaktionen aus.

**Anruf-Pipeline:**
Dashboard → `POST /calls` → Twilio-Anruf (nur Practice-Nummer, `assert_dialable` Gate) → IVR-Navigation (DTMF) → Bridge zu ElevenLabs Conversational AI → Live-Tools (`record_finding`, `validate_id`, `end_call`) → Post-Call-Webhook → `finalize_call()` → Abgleich → Mail → Dashboard.

**Zwei Lanes:**
1. **Verification + Mail** (`reconcile.py` → `summary.py` → `email_agent.py`): Vergleicht `CallResult` gegen `fixtures.json`, erzeugt deutsche Zusammenfassung, verschickt per Resend (oder Mock in `outbox/`).
2. **Telefonie** (`main.py` → `elevenlabs_client.place_call_via_elevenlabs()`): Nativer ElevenLabs-Outbound-Weg — ElevenLabs orchestriert den Twilio-Anruf selbst. `telephony.py` (Twilio-TwiML-Bridge) existiert noch, wird aber nicht mehr verwendet.

**Schlüssel-Datenfluss in `finalize_call(call_id)`** (`app/finalize.py`):
`get_live()` → `get_case()` → coerce + derive → `build_notes()` → `CallResult` → `_fire_triggers()` → `reconcile()` → `build_email_summary()` → `send_summary_email()` → `save_result()`.

**Datenmodelle** (`app/schema.py`): `CallResult` (Pydantic), Enums `CallStatus`, `MeterStatus`, `NextAction`, `ReconciliationItem`, `ReconciliationReport`.

## Wichtige Konventionen

- **Compliance-Gate:** `assert_dialable()` in `app/config.py` — nur die `PRACTICE_CLERK_NUMBER` darf gewählt werden. Niemals umgehen.
- **KI-Offenlegung:** EU AI Act — Agent muss sich als KI vorstellen, bevor er mit einem Menschen spricht.
- **Keine erfundenen Daten:** Agent darf nie Werte fabrizieren. Fehlende Felder bleiben leer/offen.
- **Secrets:** Nur über `os.environ`/`python-dotenv`, nie hartkodiert. `.env` nie committen.
- **Mail-Modi:** `EMAIL_MODE=mock` (Default, schreibt in `outbox/`) | `EMAIL_MODE=smtp` (SMTP via `smtplib`, z.B. Gmail App-Passwort) | `EMAIL_MODE=resend` (Resend-API via `httpx`). SMTP-Variablen: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`.
- **Zusammenfassung:** OpenAI mit deterministischem Template-Fallback (funktioniert immer, auch ohne Key).
- **Persistenz:** JSON-basiert in `data/results.json` (thread-safe via `_lock` in `store.py`).
- **Fixtures:** `fixtures.json` enthält 3 synthetische Fälle (CASE-A/B/C). Loader in `app/fixtures.py` (`get_case`, `list_cases`, `build_dynamic_variables`).

## Live-Anruf starten & Troubleshooting (aus der Praxis)

**Ablauf für einen echten Anruf** (zwei Prozesse parallel):
1. Terminal 1: `uvicorn app.main:app --reload`
2. Terminal 2: `ngrok http 8000` → die `https://…ngrok-free.dev`-URL kopieren (ngrok braucht einmalig `ngrok config add-authtoken <token>`).
3. Diese URL in `.env` als `PUBLIC_BASE_URL` eintragen — muss **exakt** die aktuell laufende ngrok-URL sein.
4. Konfig prüfen: `curl -s localhost:8000/health` → alle Felder inkl. `elevenlabs_phone_id_looks_valid` müssen `true` sein.
5. Anruf auslösen (Alternative zum Dashboard-Button):
   `curl -s -X POST localhost:8000/calls -H "Content-Type: application/json" -d '{"case_id":"CASE-A"}'`
   - `{"dry_run": true}` bereitet dynamic vars + TwiML vor, **ohne** zu wählen.
   - `{"ivr_digit":"2"}` überschreibt die Menü-Taste (z.B. für den Simulator).

**⚠️ Settings sind gecacht** (`@lru_cache` auf `get_settings()` in `app/config.py`): Nach **jeder** `.env`-Änderung muss uvicorn neu gestartet werden, sonst greifen die neuen Werte nicht. Symptom aus der Praxis: `/health` meldet `twilio_configured: false`, obwohl die Keys in `.env` stehen → Server läuft noch mit altem Cache. Fix: `pkill -f "uvicorn app.main:app"`, dann neu starten.

**⚠️ `ELEVENLABS_PHONE_NUMBER_ID`:** Das ist **keine Telefonnummer** (`+1…`), sondern eine ElevenLabs-interne ID (`phnum_…`). Erzeugt im EL-Dashboard unter Phone Numbers → "Import from Twilio". Steht `+1…` drin, schlägt der Anruf mit 422 fehl. Der Health-Endpoint zeigt `elevenlabs_phone_id_looks_valid: false` als Frühwarnung.

**⚠️ Webhook-Erreichbarkeit:** ElevenLabs erreicht den Post-Call-Webhook **nur** über `PUBLIC_BASE_URL`. Passt die ngrok-URL nicht (z.B. nach ngrok-Neustart), kommt kein Post-Call-Event → `finalize_call()` wird nie ausgelöst, keine Mail.

**E-Mail-Provider — was real funktioniert (hart erarbeitet):**
- ✅ **Gmail-SMTP** = der zuverlässige Weg ohne eigene Domain: `EMAIL_MODE=smtp`, `SMTP_HOST=smtp.gmail.com`, `SMTP_PORT=587`, `SMTP_USER=<gmail>`, `SMTP_PASSWORD=<16-stelliges App-Passwort>`. Voraussetzung: Google-2FA aktiv → App-Passwort erzeugen → **Leerzeichen entfernen**.
- ❌ **Outlook/Microsoft-SMTP geht NICHT** — Microsoft hat `SmtpClientAuthentication` für Privatkonten deaktiviert (Fehler `535 … SmtpClientAuthentication is disabled`). Nicht reparierbar.
- ⚠️ **Resend** braucht eine **verifizierte Domain**, sonst `403 Forbidden`; ohne Domain nur Versand an die eigene Resend-Konto-Adresse. Für echte externe Empfänger: Domain-DNS-Records (z.B. bei IONOS) verifizieren.
- 🟢 **`EMAIL_MODE=mock`** = immer demobar ohne Keys; Mail landet als `.eml`/`.html` in `outbox/`.
