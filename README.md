# Intelligent Email Triage Agent

A Python background service that monitors a Gmail inbox, classifies emails as
HIGH or LOW priority via an LLM Router Gateway (Gemini ↔ OpenAI), pushes
HIGH alerts to Telegram instantly, and batches LOW emails into a daily digest.

## Architecture

```
   ┌──────────────┐    poll       ┌──────────────────┐
   │  Gmail API   │ ────────────► │  gmail_service   │
   └──────────────┘               └────────┬─────────┘
                                           ▼
                                   ┌───────────────┐
                                   │  classifier   │  ← prompts/
                                   └───────┬───────┘
                                           ▼
                              ┌───────────────────────┐
                              │ llm.LLMRouter         │
                              │  primary → fallback   │
                              │  GEMINI ⇄ OPENAI      │
                              └──────┬─────────┬──────┘
                            HIGH ◄───┘         └──► LOW
                              │                     │
                              ▼                     ▼
                   ┌────────────────────┐   ┌────────────────┐
                   │ notifier.telegram  │   │ database       │
                   │   (instant alert)  │   │ digest_queue   │
                   └────────────────────┘   └───────┬────────┘
                                       cron @20:00 │
                                                   ▼
                                       notifier.telegram digest
```

## Project layout

```
triage-system/
├── main.py                     # Only root module — scheduler entry point
├── core/                       # Foundation
│   ├── __init__.py
│   ├── config.py               # Env loading, model IDs, provider validation
│   ├── database.py             # SQLite: processed_emails + digest_queue
│   └── schema.py               # Pydantic TriageResult — LLM output contract
├── pipeline/                   # Triage logic
│   ├── __init__.py
│   ├── classifier.py           # Router + prompt + TriageResult validation
│   ├── digest.py               # LOW-priority queue + daily flush
│   └── poll_once.py            # One-shot CI runner (python -m pipeline.poll_once)
├── prompts/
│   ├── __init__.py
│   └── triage_prompt.py        # SYSTEM_PROMPT + USER_TEMPLATE + builder
├── llm/                        # LLM Router Gateway
│   ├── __init__.py
│   ├── base.py                 # LLMProvider ABC (complete + response_schema)
│   ├── router.py               # Primary → fallback dispatch
│   ├── gemini_provider.py      # Gemini via google-genai SDK (response_schema)
│   └── openai_provider.py      # OpenAI gpt-4o-mini (structured outputs)
├── gmail_service/
│   ├── __init__.py
│   ├── auth.py                 # OAuth2 flow + token caching
│   ├── parser.py               # MIME walk, HTML strip, headers
│   └── client.py               # fetch_unread_emails()
├── notifier/
│   ├── __init__.py
│   ├── formatters.py           # Message formatting + digest chunking
│   └── telegram.py             # Telegram Bot API sender
├── scripts/                    # smoke_test.py, encode_token.py
├── requirements.txt
├── .env.example
└── README.md
```

### Adding a new LLM provider

1. Create `llm/<name>_provider.py` subclassing `LLMProvider` from `llm/base.py`.
   Implement `complete(system_prompt, user_message, response_schema=None)` —
   honor `response_schema` (a Pydantic model) for native structured output.
2. Register it in `_PROVIDER_REGISTRY` inside `llm/router.py`.
3. Add the provider key to `VALID_PROVIDERS` in `core/config.py`.

## Setup

### 1. Install dependencies

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Get API credentials

- **Gemini**: https://aistudio.google.com/apikey
- **OpenAI**: https://platform.openai.com/api-keys
- **Telegram Bot**: message `@BotFather` → `/newbot` → copy token.
  Then message the bot once and visit `https://api.telegram.org/bot<TOKEN>/getUpdates`
  to grab your `chat_id`.
- **Gmail API**: at console.cloud.google.com create a project, enable Gmail API,
  create OAuth2 desktop credentials, download as `credentials.json`, drop it next
  to `main.py`. Add yourself as test user on the OAuth consent screen.

### 3. Configure `.env`

```
cp .env.example .env
```

Fill in the keys. `LLM_PROVIDER` chooses the primary; the other is automatic
fallback.

### Environment reference

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `GEMINI_API_KEY` | yes (if primary/fallback uses it) | — | AI Studio key |
| `OPENAI_API_KEY` | yes (if primary/fallback uses it) | — | platform.openai.com key |
| `LLM_PROVIDER` | yes | `GEMINI` | Primary provider: `GEMINI` or `OPENAI` |
| `GEMINI_MODEL` | no | `gemini-2.5-flash-lite` | Gemini model ID |
| `OPENAI_MODEL` | no | `gpt-4o-mini` | OpenAI model ID |
| `TELEGRAM_BOT_TOKEN` | yes | — | From `@BotFather` |
| `TELEGRAM_CHAT_ID` | yes | — | Your chat with the bot |
| `GMAIL_CREDENTIALS_PATH` | no | `credentials.json` | OAuth client file |
| `GMAIL_TOKEN_PATH` | no | `token.json` | Cached refresh token |
| `POLL_INTERVAL_SECONDS` | no | `300` | Gmail poll cadence |
| `DIGEST_HOUR` | no | `20` | Local hour for daily digest |
| `DB_PATH` | no | `triage.db` | SQLite file |

### 4. Run

```powershell
python main.py
```

First run will open a browser for Gmail OAuth and cache `token.json`.

### Smoke tests (one-off, no scheduler)

```powershell
# Telegram round-trip
python -c "from notifier import send_test_message; print(send_test_message('hello'))"

# LLM router round-trip
python -c "from llm import LLMRouter; from config import LLM_PROVIDER, FALLBACK_PROVIDER; r = LLMRouter(LLM_PROVIDER, FALLBACK_PROVIDER); print(r.complete('Reply with the word OK only.', 'ping')); print('via:', r.last_provider_used)"

# Gmail fetch (first 3 unread)
python -c "from gmail_service import fetch_unread_emails; [print(e['sender'], '|', e['subject']) for e in fetch_unread_emails(3)]"

# Full classification on a synthetic email
python -c "from classifier import classify_email; import json; print(json.dumps(classify_email({'id':'t1','sender':'hr@acme.com','subject':'Interview invite Friday','body':'We would like to invite you for an interview.','timestamp':''}), indent=2))"
```

## LLM Router behavior

- `complete()` tries `primary` then `fallback`.
- Each provider call is independently logged.
- If both fail → `RouterExhaustedException`, classifier defaults to a **HIGH**
  `TriageResult` (reason in `step4_self_check`) so nothing is silently dropped.
- The chosen provider is set on the result as `llm_provider_used` and
  surfaced in the Telegram alert footer.
- `complete()` accepts an optional `response_schema` (a Pydantic model) and
  forwards it to the provider for native structured output.

## Classification prompt

The full system prompt lives in [`prompts/triage_prompt.py`](prompts/triage_prompt.py).
It is a 5-step reasoning chain:

1. **Identify category** (JOB, FINANCIAL, DEADLINE, OTP_SECURITY, NEWSLETTER,
   SOCIAL, PERSONAL, UNKNOWN)
2. **Assess urgency** — three YES/NO checks (24h action, risk, harm if ignored)
3. **Classify priority** — HIGH or LOW
4. **Self-check** — guard against over/under-triage, declare confidence
5. **Compose message** — 3-line Telegram alert or 15-word digest line

### Structured output

The output contract is the Pydantic model `TriageResult` in
[`core/schema.py`](core/schema.py). It is enforced at generation time, not just parsed
afterwards:

- **Gemini** — the model is passed as `response_schema` (with
  `response_mime_type=application/json`).
- **OpenAI** — sent via `beta.chat.completions.parse` with the model as
  `response_format` (strict structured outputs).

The raw response is then validated with `TriageResult.model_validate_json()`.
A trailing-comma strip in `classifier._parse_result()` is kept as a
last-resort fallback. Any validation failure falls through to the safe-HIGH
default, so a malformed response can never drop an email.

### Prompt evaluation

The system prompt has been assessed against a structured prompt-quality
rubric (explicit reasoning, structured output, self-checks, fallbacks, etc.).
See [`prompt_evaluator.md`](prompt_evaluator.md) for the full criteria
breakdown and result — it scores 6/8, with the two gaps (multi-turn loop,
reasoning-type tagging) being out of scope by design.

### Example output (LOW)

```json
{
  "step1_category": "NEWSLETTER",
  "step2_urgency": {
    "action_required_24h": "NO — promotional content",
    "risk_involved": "NO — no financial or security impact",
    "harm_if_ignored": "NO — purely informational"
  },
  "step3_priority": "LOW",
  "step4_confidence": "HIGH_CONFIDENCE",
  "step4_self_check": "Standard product newsletter, safe to batch.",
  "step5_message": "Acme Weekly: new dashboards and pricing updates available.",
  "llm_provider_used": "GEMINI"
}
```

### Example Telegram alert (HIGH)

```
🚨 HIGH PRIORITY EMAIL
Interview invite from Acme Corp for Senior Engineer
Career impact — response window 48h
Reply by tomorrow to confirm slot
📁 Category: JOB
🤖 Classified by: GEMINI
```

## Scheduling

- Inbox poll: every `POLL_INTERVAL_SECONDS` (default 300)
- Daily digest: cron at `DIGEST_HOUR:00` local time (default 20:00)
- A poll runs once on startup so you don't have to wait.

## Safety / idempotency

- `processed_emails` (SQLite PK on `email_id`) prevents double-classification.
- Digest entries persist until the daily flush succeeds; on Telegram failure
  they remain `sent=0` and are retried at the next digest fire.
- Gmail scope is `gmail.readonly` — the agent never modifies your inbox.

## GitHub Actions Deployment

Run the agent in the cloud — no local machine required. A workflow polls every
4 hours and commits triage state (`triage.db`, `.digest_marker`) back to the
repo so processed-email tracking and digest-once-a-day semantics survive across
runs. You can also trigger a run on demand from the Actions tab.

### Files involved

| File | Purpose |
|------|---------|
| [`.github/workflows/triage.yml`](.github/workflows/triage.yml) | Cron schedule + manual dispatch |
| [`pipeline/poll_once.py`](pipeline/poll_once.py) | Single poll cycle, no scheduler. Calls `send_daily_digest_if_due()` |
| [`scripts/encode_token.py`](scripts/encode_token.py) | One-off helper: base64-encodes `token.json` for the `GMAIL_TOKEN` secret |

### One-time setup

1. **Complete Gmail OAuth locally first.** Run `python main.py` once on your
   machine so `token.json` is created and refresh-token cached.

2. **Encode the token for GitHub.**

   ```powershell
   python scripts/encode_token.py
   ```

   Copy the base64 blob it prints.

3. **Push the repo to GitHub** (a private repo is recommended — `triage.db`
   contains processed-email IDs).

4. **Add the following GitHub Secrets** — repo → Settings → Secrets and
   variables → Actions → New repository secret:

   | Secret name | Value |
   |-------------|-------|
   | `GEMINI_API_KEY` | Your Google AI Studio key |
   | `OPENAI_API_KEY` | Your platform.openai.com key |
   | `TELEGRAM_BOT_TOKEN` | From `@BotFather` |
   | `TELEGRAM_CHAT_ID` | Your chat ID with the bot |
   | `GMAIL_TOKEN` | The base64 blob from `scripts/encode_token.py` |

5. **Enable Actions** if disabled — repo → Actions → "I understand my
   workflows, go ahead and enable them".

6. **Trigger the workflow manually the first time** — Actions tab →
   "triage" → "Run workflow". Verify the run succeeds end-to-end before
   leaving it on cron.

### How the schedule works

- The workflow cron is `0 */4 * * *` — every 4 hours, at 00:00, 04:00, 08:00,
  12:00, 16:00, 20:00 UTC.
- **Run on demand**: Actions tab → "triage" → "Run workflow". Use this for a
  live demo instead of waiting for the next 4-hour tick.
- `DIGEST_HOUR=14` (workflow env, UTC) means the digest fires on the first
  poll **at or after** 14:00 UTC each day — i.e. the 16:00 UTC run (≈ 21:30
  IST). Set any value `0–20`; it must be ≤ 20 so a poll still occurs that day.
- `send_daily_digest_if_due()` uses `utc_hour >= DIGEST_HOUR` and writes
  `.digest_marker` (today's date), so the digest goes out once per day even if
  the run nearest `DIGEST_HOUR` is delayed or skipped by GitHub cron jitter.

### Security notes

- `token.json` is decoded from the secret at job start and `rm -f`'d in an
  `if: always()` cleanup step.
- `credentials.json` is **never** uploaded — refresh tokens in `token.json`
  are sufficient at runtime.
- The committed `triage.db` contains Gmail message IDs but no message
  content. Still, prefer a private repo.

## Smoke Tests (cloud pipeline)

A successful manual run looks roughly like this in the Actions log:

```
Run python -m pipeline.poll_once
2026-05-21 14:00:12 [INFO] triage.oneshot: Database initialized
2026-05-21 14:00:12 [INFO] triage.oneshot: Polling Gmail inbox (one-shot)...
2026-05-21 14:00:14 [INFO] triage.oneshot: Fetched 3 unread email(s)
2026-05-21 14:00:14 [INFO] llm.router: Trying provider: GEMINI
2026-05-21 14:00:16 [INFO] triage.oneshot: Email 18f...a1 -> HIGH (provider=GEMINI)
2026-05-21 14:00:16 [INFO] llm.router: Trying provider: GEMINI
2026-05-21 14:00:17 [INFO] triage.oneshot: Email 18f...a2 -> LOW  (provider=GEMINI)
2026-05-21 14:00:18 [INFO] triage.oneshot: Email 18f...a3 -> LOW  (provider=GEMINI)
2026-05-21 14:00:18 [INFO] triage.oneshot: Digest hour reached but no pending entries; not marking
2026-05-21 14:00:18 [INFO] triage.oneshot: One-shot poll complete (handled=3)
Run git config user.name  "triage-bot"
[main 4a9b1c2] chore(triage): update state [skip ci]
 2 files changed, 0 insertions(+), 0 deletions(-)
```

Sample Telegram notification you should receive seconds after a HIGH classification:

```
🚨 HIGH PRIORITY EMAIL
Interview invite — Acme Corp, Senior Engineer role
Career impact, response window 48h
Reply by tomorrow to confirm the Friday 3pm slot
📁 Category: JOB
🤖 Classified by: GEMINI
```

And the daily digest (delivered once per UTC day at `DIGEST_HOUR`):

```
📋 Daily Email Digest (4 items)
1. Acme Weekly: new dashboards and pricing updates available.
2. LinkedIn: 3 new posts from your network.
3. GitHub: weekly digest of starred repo activity.
4. Medium Daily Digest — 5 stories picked for you.
```

### Troubleshooting cloud runs

| Symptom | Cause / Fix |
|---------|-------------|
| Workflow exits with "GMAIL_TOKEN secret is empty" | Secret not set or wrong name |
| `RefreshError: invalid_grant` in logs | Token expired or revoked. Re-run OAuth locally and re-encode |
| Workflow runs but no Telegram message | Check the **Telegram round-trip** smoke test locally first |
| Two digests on the same day | Confirm `.digest_marker` was committed back by the previous run — check the run's commit |
| 403 on `git push` | Repo Actions setting → "Workflow permissions" → enable "Read and write permissions" |

## Operational notes

- `token.json` is generated on first auth and refreshes itself. Delete it to
  re-auth.
- `triage.db` accumulates processed IDs; safe to delete to re-process unread
  mail (but you may get duplicate alerts).
- Logs go to stdout. Pipe to a file or `journalctl` in production.
