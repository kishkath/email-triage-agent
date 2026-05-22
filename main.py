import logging
import signal
import sys
import time

from apscheduler.schedulers.background import BackgroundScheduler

import gmail_service
import notifier
from core import database
from core.config import POLL_INTERVAL_SECONDS, DIGEST_HOUR
from core.schema import Priority
from pipeline import classify_email, digest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("triage")


def process_inbox() -> None:
    log.info("Polling Gmail inbox...")
    try:
        emails = gmail_service.fetch_unread_emails()
    except Exception as e:  # noqa: BLE001
        log.exception("Gmail fetch failed: %s", e)
        return

    log.info("Fetched %d unread email(s)", len(emails))
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


def send_daily_digest() -> None:
    log.info("Daily digest job firing")
    digest.flush_digest()


def main() -> None:
    database.init_db()
    log.info("Database initialized")

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        process_inbox,
        "interval",
        seconds=POLL_INTERVAL_SECONDS,
        id="poll_inbox",
        max_instances=1,
    )
    scheduler.add_job(
        send_daily_digest,
        "cron",
        hour=DIGEST_HOUR,
        minute=0,
        id="daily_digest",
    )
    scheduler.start()
    log.info("Scheduler started. Poll=%ss, digest hour=%s", POLL_INTERVAL_SECONDS, DIGEST_HOUR)

    process_inbox()

    def _shutdown(signum, frame):  # noqa: ARG001
        log.info("Shutting down...")
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    try:
        signal.signal(signal.SIGTERM, _shutdown)
    except (AttributeError, ValueError):
        pass

    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        _shutdown(None, None)


if __name__ == "__main__":
    main()
