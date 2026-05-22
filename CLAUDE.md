# CLAUDE.md

Guidance for Claude Code sessions working in this repo.

## What this project is

A polling background service (`python main.py`) that reads unread Gmail, asks an
LLM to triage each email as HIGH or LOW priority, fires Telegram alerts for
HIGH and batches LOW into a daily digest. The LLM call goes through a small
**Router Gateway** that supports Gemini (primary) and OpenAI (fallback).

The user is an engineer building this as a learning project (TSAI Agentic
coursework). Prefer clear, modular code over clever code.

## Module ownership — where things live

| Concern | Module | Notes |
|---------|--------|-------|
| Env loading, model IDs, constants | `core/config.py` | Validates `LLM_PROVIDER`; derives `FALLBACK_PROVIDER` |
| SQLite | `core/database.py` | `processed_emails` PK = `email_id`; `digest_queue` |
| Output schema | `core/schema.py` | Pydantic `TriageResult` + `StrEnum`s — LLM output contract |
| Triage prompt | `prompts/triage_prompt.py` | `SYSTEM_PROMPT`, `USER_TEMPLATE`, `build_user_message()` |
| LLM Router Gateway | `llm/router.py` | Tries primary → fallback; raises `RouterExhaustedException` |
| LLM providers | `llm/gemini_provider.py`, `llm/openai_provider.py` | Both subclass `llm.base.LLMProvider` |
| Gmail OAuth + fetch | `gmail_service/{auth,parser,client}.py` | `gmail.readonly` scope only |
| Telegram I/O | `notifier/telegram.py` + `notifier/formatters.py` | Plain `requests`, no `python-telegram-bot` |
| Classifier orchestration | `pipeline/classifier.py` | Calls router, validates `TriageResult`, safe HIGH default |
| Digest queue + flush | `pipeline/digest.py` | Thin wrapper over `core.database` + `notifier` |
| One-shot CI runner | `pipeline/poll_once.py` | `python -m pipeline.poll_once`; digest-due check |
| Entry point + scheduler | `main.py` | Only root module. APScheduler: interval poll + daily cron |

## Hard rules (don't break these)

1. **Don't widen the Gmail scope** beyond `gmail.readonly`. The agent never
   modifies the user's inbox. If a feature seems to need write access, ask.
2. **Don't change the system prompt without checking with the user.** The
   prompt in `prompts/triage_prompt.py` is the spec. Em-dashes (`—`), step
   headers, JSON schema, and error-handling clauses are intentional.
3. **Gemini uses the `google-genai` SDK** (not the deprecated
   `google-generativeai`). Model defaults to `gemini-2.5-flash-lite` and is
   overridable via the `GEMINI_MODEL` env var — the user opted for the latest
   free lite model. Don't pin a model in code; keep it env-configurable.
4. **The classifier must never drop an email silently.** All error paths
   (`router_exhausted`, `parse_error`) fall through to `_default_high()`
   which returns a `TriageResult` with priority=HIGH and the reason recorded
   in `step4_self_check`. Preserve this.
5. **`schema.TriageResult` is the LLM output contract.** It is sent to
   providers as the native response schema *and* validates the response.
   If you change its fields, also update `prompts/triage_prompt.py` so the
   prompt's JSON spec stays in sync — and check rule #2 first.
6. **Idempotency via `processed_emails` PK.** Don't switch to anything that
   could double-classify on overlapping polls.
7. **Don't commit `.env`, `token.json`, `credentials.json`, or `*.db`.**
   They're gitignored — keep it that way.

## Conventions

- **Imports**: package-style. `from core.config import LLM_PROVIDER`,
  `from core import database`, `from pipeline import classify_email`,
  `from llm import LLMRouter`, `import notifier`. Relative imports
  (`from .config import ...`) are used *within* a package only.
- **Layout**: `main.py` is the only module in the repo root. Everything else
  lives in a package — `core/` (config, database, schema), `pipeline/`
  (classifier, digest, poll_once), `prompts/`, `llm/`, `gmail_service/`,
  `notifier/`.
- **Logging**: stdlib `logging`, module-level `log = logging.getLogger(__name__)`.
  Don't introduce `print()` in library code.
- **Time**: `datetime.now(timezone.utc)`. Do not use deprecated `datetime.utcnow()`.
- **Errors**: catch broadly only at scheduler boundaries (`main.process_inbox`,
  `pipeline.poll_once`) and provider calls (`llm.router`). Library functions raise.
- **No comments unless the *why* is non-obvious.** Names should carry intent.

## Adding a new LLM provider

1. Create `llm/<name>_provider.py`. Subclass `LLMProvider` (`llm/base.py`),
   set `name`, implement `complete(system_prompt, user_message) -> str`.
2. Register the class in `_PROVIDER_REGISTRY` in `llm/router.py`.
3. Add the key to `VALID_PROVIDERS` in `core/config.py`.
4. Add any required env var(s) to `core/config.py` and `.env.example`.

The router is provider-agnostic — do not embed provider-specific logic in
`router.py`. All SDK calls and shape-coercion belong inside the provider class.

## Running and testing

```powershell
# Setup
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Run
python main.py
```

Smoke-test snippets live in the README under "Smoke tests". Use those before
asking the user to run the full polling loop.

The Python launcher is `py` on this Windows host (`python` may resolve to the
Microsoft Store stub). Use `py` for one-off invocations in Bash; PowerShell
inside a venv uses `python` normally.

## What's intentionally not here

- **No tests directory.** This is a small learning project; user has not
  asked for pytest. Don't scaffold one unless asked.
- **No retries/backoff on Gmail or Telegram beyond a single attempt.**
  Telegram digest entries stay pending in SQLite and retry next cycle; poll
  failures just log and wait for the next interval. Adequate for the use case.
- **No async.** Scheduler runs sync jobs in threads. Don't introduce
  `asyncio` — `requests`, `google-genai`, and `openai` sync clients
  are all fine here.
- **No `python-telegram-bot`** despite the original spec mentioning it. We
  use plain `requests` to keep the dependency surface small.

## Known quirks

- If Gemini returns 404 "model not found", the `GEMINI_MODEL` value isn't
  available on the user's key. Surface it and suggest setting a different
  free model via the `GEMINI_MODEL` env var — don't hard-code a swap.
- Gemini's `response_schema` converter rejects a `default` key in the JSON
  schema. Keep all `TriageResult` fields required (no Pydantic defaults).
- Structured output is enforced at generation time: `classify_email()` passes
  `TriageResult` to the router, Gemini receives it as `response_schema` and
  OpenAI via `beta.chat.completions.parse`. The classifier's trailing-comma
  strip in `_parse_result()` is kept as a last-resort fallback (covers the
  no-schema path and provider edge cases); don't remove it.
- NVIDIA NIM was the original fallback provider; it was swapped for OpenAI at
  the user's request. The provider pattern (`llm/base.py` + registry) makes
  re-adding NIM trivial if needed later.
- Daily digest uses a cron trigger at `DIGEST_HOUR:00` **local time**, not
  UTC. The user is in IST. If you change to UTC, ask first.

## Useful commands

```powershell
# Re-auth Gmail
Remove-Item token.json

# Reset processed-email tracking (forces re-classification of all unread)
Remove-Item triage.db

# Tail logs while running
python main.py 2>&1 | Tee-Object -FilePath triage.log
```
