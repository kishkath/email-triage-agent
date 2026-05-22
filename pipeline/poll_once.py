"""Single-shot poll cycle for headless / CI execution (GitHub Actions).

No scheduler, no infinite loop. Fetches unread Gmail, classifies each email
via the LLM router, dispatches HIGH alerts and queues LOW for digest. Fires
the daily digest on the first poll at/after DIGEST_HOUR (UTC) that has not
already sent today (tracked via .digest_marker).
"""

import logging
import sys
from datetime import datetime, timezone

import gmail_service
import notifier
from core import database
from core.config import DIGEST_HOUR, ROOT
from core.schema import Priority
from . import digest
from .classifier import classify_email

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("triage.oneshot")

_DIGEST_MARKER = ROOT / ".digest_marker"


def process_inbox() -> int:
    log.info("Polling Gmail inbox (one-shot)...")
    emails = gmail_service.fetch_unread_emails()
    log.info("Fetched %d unread email(s)", len(emails))

    handled = 0
    for email in emails:
        eid = email["id"]
        if database.is_processed(eid):
            continue
        try:
            result = classify_email(email)
        except Exception as e:  # noqa: BLE001
            log.exception("Classification failed for %s: %s", eid, e)
            continue

        priority = result.step3_priority
        provider = result.llm_provider_used or "UNKNOWN"
        log.info("Email %s -> %s (provider=%s)", eid, priority, provider)

        if priority == Priority.HIGH:
            notifier.send_high_priority_alert(result)
        else:
            digest.queue_low_priority(eid, result.step5_message)

        database.mark_processed(eid, provider)
        handled += 1
    return handled


def _read_marker() -> str:
    if _DIGEST_MARKER.exists():
        return _DIGEST_MARKER.read_text(encoding="utf-8").strip()
    return ""


def _write_marker(date_str: str) -> None:
    _DIGEST_MARKER.write_text(date_str, encoding="utf-8")


def send_daily_digest_if_due() -> bool:
    """Fire the digest once per UTC day, on the first poll at/after DIGEST_HOUR.

    Using >= (rather than an exact hour match) keeps this robust to a coarse
    poll cadence and GitHub cron jitter — if the run nearest DIGEST_HOUR is
    delayed or skipped, the next poll that day still sends it.

    Returns True if a digest was sent this invocation.
    """
    now = datetime.now(timezone.utc)
    today = now.date().isoformat()

    if now.hour < DIGEST_HOUR:
        log.info("Digest not due yet (utc_hour=%d, target>=%d)", now.hour, DIGEST_HOUR)
        return False
    if _read_marker() == today:
        log.info("Digest already sent today (%s)", today)
        return False

    sent = digest.flush_digest()
    if sent > 0:
        _write_marker(today)
        log.info("Digest fired (%d entries) and marker updated", sent)
        return True
    log.info("Digest hour reached but no pending entries; not marking")
    return False


def main() -> int:
    database.init_db()
    log.info("Database initialized")
    try:
        handled = process_inbox()
    except Exception as e:  # noqa: BLE001
        log.exception("Inbox processing failed: %s", e)
        handled = 0

    try:
        send_daily_digest_if_due()
    except Exception as e:  # noqa: BLE001
        log.exception("Digest check failed: %s", e)

    log.info("One-shot poll complete (handled=%d)", handled)
    return 0


if __name__ == "__main__":
    sys.exit(main())
