"""Smoke test — verifies each component before running the full agent.

Run from the triage-system directory so .env and credentials.json resolve:

    uv run --no-project --with-requirements requirements.txt python scripts/smoke_test.py

Pass --no-gmail to skip the Gmail check (it opens a browser on first run).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

PASS = "[ PASS ]"
FAIL = "[ FAIL ]"
SKIP = "[ SKIP ]"


def check_config() -> bool:
    try:
        from core import config

        missing = []
        if not config.GEMINI_API_KEY:
            missing.append("GEMINI_API_KEY")
        if not config.OPENAI_API_KEY:
            missing.append("OPENAI_API_KEY")
        if not config.TELEGRAM_BOT_TOKEN:
            missing.append("TELEGRAM_BOT_TOKEN")
        if not config.TELEGRAM_CHAT_ID:
            missing.append("TELEGRAM_CHAT_ID")
        print(f"  primary={config.LLM_PROVIDER}  fallback={config.FALLBACK_PROVIDER}")
        if missing:
            print(f"{FAIL} config — missing .env values: {', '.join(missing)}")
            return False
        print(f"{PASS} config — all keys present")
        return True
    except Exception as e:  # noqa: BLE001
        print(f"{FAIL} config — {e}")
        return False


def check_database() -> bool:
    try:
        from core import database

        database.init_db()
        print(f"{PASS} database — tables initialized")
        return True
    except Exception as e:  # noqa: BLE001
        print(f"{FAIL} database — {e}")
        return False


def check_telegram() -> bool:
    try:
        from notifier import send_test_message

        if send_test_message("Triage agent smoke test ✅"):
            print(f"{PASS} telegram — message sent (check your chat)")
            return True
        print(f"{FAIL} telegram — send returned False (check token / chat_id)")
        return False
    except Exception as e:  # noqa: BLE001
        print(f"{FAIL} telegram — {e}")
        return False


def check_llm_router() -> bool:
    try:
        from core.config import LLM_PROVIDER, FALLBACK_PROVIDER
        from llm import LLMRouter

        router = LLMRouter(primary=LLM_PROVIDER, fallback=FALLBACK_PROVIDER)
        reply = router.complete("Reply with the single word OK.", "ping")
        print(f"  reply={reply.strip()[:60]!r}  via={router.last_provider_used}")
        print(f"{PASS} llm router — {router.last_provider_used} responded")
        return True
    except Exception as e:  # noqa: BLE001
        print(f"{FAIL} llm router — {e}")
        return False


def check_classifier() -> bool:
    try:
        from pipeline import classify_email

        result = classify_email(
            {
                "id": "smoke-1",
                "sender": "hr@acme.com",
                "subject": "Interview invite — Friday 3pm",
                "body": "We would like to invite you to an interview this Friday.",
                "timestamp": "",
            }
        )
        print(
            f"  priority={result.step3_priority}  "
            f"category={result.step1_category}  "
            f"provider={result.llm_provider_used}"
        )
        print(f"{PASS} classifier — returned a validated TriageResult")
        return True
    except Exception as e:  # noqa: BLE001
        print(f"{FAIL} classifier — {e}")
        return False


def check_gmail() -> bool:
    try:
        from gmail_service import fetch_unread_emails

        emails = fetch_unread_emails(3)
        print(f"  fetched {len(emails)} unread email(s)")
        for e in emails:
            print(f"    - {e['sender']} | {e['subject']}")
        print(f"{PASS} gmail — auth OK, fetch OK")
        return True
    except Exception as e:  # noqa: BLE001
        print(f"{FAIL} gmail — {e}")
        return False


def main() -> int:
    skip_gmail = "--no-gmail" in sys.argv
    print("=" * 60)
    print("EMAIL TRIAGE AGENT — SMOKE TEST")
    print("=" * 60)

    results = {
        "config": check_config(),
        "database": check_database(),
        "telegram": check_telegram(),
        "llm router": check_llm_router(),
        "classifier": check_classifier(),
    }

    if skip_gmail:
        print(f"{SKIP} gmail — skipped (--no-gmail)")
    else:
        results["gmail"] = check_gmail()

    print("=" * 60)
    passed = sum(1 for ok in results.values() if ok)
    total = len(results)
    print(f"RESULT: {passed}/{total} checks passed")
    print("=" * 60)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
