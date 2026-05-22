import logging
import requests

from core.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from .formatters import chunk_digest, format_digest_header, format_high_priority

log = logging.getLogger(__name__)
_API = "https://api.telegram.org/bot{token}/sendMessage"


def _send(text: str) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        log.error("Telegram credentials not configured")
        return False
    url = _API.format(token=TELEGRAM_BOT_TOKEN)
    try:
        r = requests.post(
            url,
            json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "disable_web_page_preview": True},
            timeout=15,
        )
        if r.status_code != 200:
            log.error("Telegram send failed: %s %s", r.status_code, r.text)
            return False
        return True
    except requests.RequestException as e:
        log.error("Telegram request error: %s", e)
        return False


def send_high_priority_alert(result) -> bool:
    return _send(format_high_priority(result))


def send_digest(digest_lines: list[str]) -> bool:
    if not digest_lines:
        return False
    header = format_digest_header(len(digest_lines))
    for part in chunk_digest(digest_lines, header):
        if not _send(part):
            return False
    return True


def send_test_message(text: str = "Triage agent online.") -> bool:
    return _send(text)
