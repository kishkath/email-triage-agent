import base64
from bs4 import BeautifulSoup


def _decode_part(data: str) -> str:
    try:
        return base64.urlsafe_b64decode(data.encode()).decode("utf-8", errors="ignore")
    except Exception:
        return ""


def extract_body(payload: dict) -> str:
    if not payload:
        return ""
    mime = payload.get("mimeType", "")
    if not mime.startswith(("text/", "multipart/")):
        return ""
    body = payload.get("body", {})
    data = body.get("data")

    if data and mime == "text/plain":
        return _decode_part(data)
    if data and mime == "text/html":
        return BeautifulSoup(_decode_part(data), "html.parser").get_text(" ", strip=True)

    for part in payload.get("parts", []) or []:
        text = extract_body(part)
        if text:
            return text
    return ""


def truncate_words(text: str, max_words: int = 300) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words])


def header(headers: list, name: str) -> str:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""
