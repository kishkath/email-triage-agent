import logging

import notifier
from core import database

log = logging.getLogger(__name__)


def queue_low_priority(email_id: str, digest_line: str) -> None:
    database.add_to_digest(email_id, digest_line)


def flush_digest() -> int:
    lines = database.get_pending_digest()
    if not lines:
        log.info("No digest entries to send")
        return 0
    ok = notifier.send_digest(lines)
    if ok:
        database.mark_digest_sent()
        log.info("Sent digest with %d entries", len(lines))
        return len(lines)
    log.error("Failed to send digest; entries left pending")
    return 0
