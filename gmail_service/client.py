import logging
from email.utils import parsedate_to_datetime

from .auth import get_service
from .parser import extract_body, header, truncate_words

log = logging.getLogger(__name__)


def fetch_unread_emails(max_results: int = 25) -> list[dict]:
    service = get_service()
    resp = (
        service.users()
        .messages()
        .list(userId="me", labelIds=["INBOX", "UNREAD"], maxResults=max_results)
        .execute()
    )
    messages = resp.get("messages", []) or []
    out = []
    for m in messages:
        try:
            msg = service.users().messages().get(userId="me", id=m["id"], format="full").execute()
            payload = msg.get("payload", {})
            headers = payload.get("headers", [])
            sender = header(headers, "From")
            subject = header(headers, "Subject")
            date_str = header(headers, "Date")
            try:
                ts = parsedate_to_datetime(date_str).isoformat() if date_str else ""
            except Exception:
                ts = date_str
            body = truncate_words(extract_body(payload), 300)
            out.append(
                {
                    "id": m["id"],
                    "sender": sender,
                    "subject": subject,
                    "body": body,
                    "timestamp": ts,
                }
            )
        except Exception as e:  # noqa: BLE001
            log.warning("Failed to fetch message %s: %s", m.get("id"), e)
    return out
