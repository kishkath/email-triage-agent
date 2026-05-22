"""Encode token.json for use as the GMAIL_TOKEN GitHub Secret.

Run this ONCE locally after you have completed Gmail OAuth (i.e. token.json
exists in the repo root). It prints a base64 string you paste into GitHub.
"""

import base64
import sys
from pathlib import Path

TOKEN_PATH = Path("token.json")


def main() -> int:
    if not TOKEN_PATH.exists():
        print("ERROR: token.json not found in current directory.", file=sys.stderr)
        print("Run `python main.py` once locally first to complete Gmail OAuth.", file=sys.stderr)
        return 1

    raw = TOKEN_PATH.read_bytes()
    encoded = base64.b64encode(raw).decode("ascii")

    print("=" * 72)
    print("GMAIL_TOKEN (base64 encoded token.json contents)")
    print("=" * 72)
    print(encoded)
    print("=" * 72)
    print()
    print("HOW TO ADD THIS TO GITHUB SECRETS:")
    print()
    print("  1. Push this repo to GitHub.")
    print("  2. Go to: Settings -> Secrets and variables -> Actions -> New repository secret")
    print("  3. Name:  GMAIL_TOKEN")
    print("  4. Value: paste the base64 string above (the line between the ===)")
    print("  5. Click 'Add secret'.")
    print()
    print("Add the other required secrets the same way:")
    print("  - GEMINI_API_KEY")
    print("  - OPENAI_API_KEY")
    print("  - TELEGRAM_BOT_TOKEN")
    print("  - TELEGRAM_CHAT_ID")
    print()
    print("Then enable Actions on the repo and trigger the 'triage' workflow")
    print("manually from the Actions tab to verify the pipeline.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
