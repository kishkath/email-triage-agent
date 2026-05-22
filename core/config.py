import os
from pathlib import Path
from dotenv import load_dotenv

# Project root = the parent of the core/ package (this file is core/config.py).
# All relative paths and the .env file resolve against this, so the app behaves
# the same regardless of the working directory it is launched from
# (python main.py, uv run, python -m pipeline.poll_once, CI, etc.).
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _resolve(value: str) -> str:
    # A Windows drive-letter path (C:\... or C:/...) is not recognized as
    # absolute by POSIX Path, which would wrongly join it onto ROOT. Detect it
    # explicitly so such a value is returned as-is rather than mangled.
    drive_letter = len(value) >= 2 and value[0].isalpha() and value[1] == ":"
    path = Path(value)
    if path.is_absolute() or drive_letter:
        return value
    return str(ROOT / path)


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "GEMINI").upper()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

GMAIL_CREDENTIALS_PATH = _resolve(os.getenv("GMAIL_CREDENTIALS_PATH", "credentials.json"))
GMAIL_TOKEN_PATH = _resolve(os.getenv("GMAIL_TOKEN_PATH", "token.json"))

POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "300"))
DIGEST_HOUR = int(os.getenv("DIGEST_HOUR", "20"))

DB_PATH = _resolve(os.getenv("DB_PATH", "triage.db"))

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

VALID_PROVIDERS = {"GEMINI", "OPENAI"}
if LLM_PROVIDER not in VALID_PROVIDERS:
    raise ValueError(f"LLM_PROVIDER must be one of {VALID_PROVIDERS}, got {LLM_PROVIDER}")

FALLBACK_PROVIDER = "OPENAI" if LLM_PROVIDER == "GEMINI" else "GEMINI"
