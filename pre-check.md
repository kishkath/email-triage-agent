# Pre-Check — Setup Guide

Follow this file top to bottom **before** running the agent. By the end you
will have a filled `.env`, a `credentials.json`, and a `token.json`.

Estimated time: ~15–20 minutes.

---

## 0. Prerequisites

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) installed (`pip install uv` if needed)
- A Google account whose Gmail inbox you want triaged
- A Telegram account

Install dependencies once:

```powershell
cd "<path-to>\triage-system"
uv venv
uv pip install -r requirements.txt
```

---

## 1. What goes in `.env`

Copy the template, then fill the blanks as you complete each section below.

```powershell
Copy-Item .env.example .env
```

| Variable | Where it comes from | Section |
|----------|--------------------|---------|
| `GEMINI_API_KEY` | Google AI Studio | [§2](#2-gemini_api_key) |
| `OPENAI_API_KEY` | OpenAI Platform | [§3](#3-openai_api_key) |
| `LLM_PROVIDER` | Leave as `GEMINI` | — |
| `TELEGRAM_BOT_TOKEN` | Telegram @BotFather | [§4](#4-telegram_bot_token--telegram_chat_id) |
| `TELEGRAM_CHAT_ID` | Telegram getUpdates API | [§4](#4-telegram_bot_token--telegram_chat_id) |
| `GMAIL_CREDENTIALS_PATH` | Leave as `credentials.json` | [§5](#5-gmail-credentialsjson--oauth) |
| `GMAIL_TOKEN_PATH` | Leave as `token.json` (auto-created) | [§5](#5-gmail-credentialsjson--oauth) |
| `POLL_INTERVAL_SECONDS` | Leave as `300` (5 min) | — |
| `DIGEST_HOUR` | Local hour for daily digest, default `20` (8 PM) | — |
| `DB_PATH` | Leave as `triage.db` | — |

---

## 2. `GEMINI_API_KEY`

1. Go to https://aistudio.google.com/apikey
2. Sign in with any Google account
3. Click **Create API key**
4. Copy the key (starts with `AIza...`)
5. Paste into `.env`:
   ```
   GEMINI_API_KEY="AIza...your_key"
   ```

Free tier is sufficient for personal use.

---

## 3. `OPENAI_API_KEY`

This is the **fallback** provider (used only if Gemini fails).

1. Go to https://platform.openai.com/api-keys
2. Sign in / create an account
3. Click **Create new secret key** → copy it (starts with `sk-...`)
4. Paste into `.env`:
   ```
   OPENAI_API_KEY="sk-...your_key"
   ```

> Note: OpenAI has no free tier — it requires a billing method. If you skip
> this, the agent still runs on Gemini alone; the fallback simply won't be
> available.

---

## 4. `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`

### 4a. Create the bot

1. Open Telegram, search for **`@BotFather`**, open the chat
2. Send `/newbot`
3. Enter a display name (e.g. `My Triage Agent`)
4. Enter a username — **must end in `bot`** (e.g. `my_triage_bot`)
5. BotFather replies with a token like `8123456789:AAH...`
6. Paste into `.env`:
   ```
   TELEGRAM_BOT_TOKEN=8123456789:AAH...your_token
   ```

### 4b. Get your chat ID

1. In Telegram, open a chat with the bot you just created
2. Press **Start** (or send any message like `hi`) — **mandatory**: the bot
   cannot message you until you message it first
3. In a browser, open (replace `<TOKEN>` with your bot token):
   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```
4. In the JSON response, find `"chat":{"id":123456789,...}`
5. The **number** is your chat ID. Paste into `.env`:
   ```
   TELEGRAM_CHAT_ID=123456789
   ```

> If the JSON shows `"result":[]` (empty), send the bot another message and
> refresh the URL.

---

## 5. Gmail `credentials.json` + OAuth

The Gmail setup produces a **file** (`credentials.json`) — you do not paste a
key into `.env`. The `.env` already points at the right paths.

### 5a. Create a Google Cloud project

1. Go to https://console.cloud.google.com
2. Top bar → project dropdown → **New Project**
3. Name it `email-triage` → **Create**
4. Make sure `email-triage` is the **selected project** in the top bar

### 5b. Enable the Gmail API

1. Left menu → **APIs & Services → Library**
2. Search **Gmail API** → click it → **Enable**

### 5c. Configure the OAuth consent screen

1. Left menu → **APIs & Services → OAuth consent screen**
2. User type: **External** → **Create**
3. Fill in:
   - App name: `email-triage`
   - User support email: your Gmail
   - Developer contact email: your Gmail
4. **Save and Continue** through the Scopes page (scopes are set in code)
5. **Save and Continue** through to the end

### 5d. Add your Gmail as a test user (IMPORTANT)

If you skip this, OAuth login fails with **"access blocked / app not
verified"**.

**Fix: add your Gmail as a test user**

1. Go to https://console.cloud.google.com
2. Top bar — make sure the **email-triage** project is selected
3. Left menu → **APIs & Services → OAuth consent screen**
4. In the current Console UI, click the **Audience** tab (left side)
5. Scroll to the **Test users** section → click **+ Add users**
6. Type the **exact Gmail address** you're trying to log in with → **Save**

> The address here MUST match the account whose inbox you want triaged and
> the account you pick during the browser login in step 5f.

### 5e. Create OAuth credentials

1. Left menu → **APIs & Services → Credentials**
2. Click **+ Create Credentials → OAuth client ID**
3. Application type: **Desktop app** → give it any name → **Create**
4. In the popup, click **Download JSON**
5. **Rename** the downloaded file to exactly **`credentials.json`**
6. **Move it** into the project folder, next to `main.py`:
   ```
   triage-system\credentials.json
   ```

### 5f. Run the one-time OAuth login

From the `triage-system` directory:

```powershell
uv run --no-project --with-requirements requirements.txt python -c "from gmail_service import fetch_unread_emails; [print(e['sender'],'|',e['subject']) for e in fetch_unread_emails(3)]"
```

- A browser window opens → choose the Gmail account you added as a test user
- You'll see **"Google hasn't verified this app"** →
  click **Advanced → Go to email-triage (unsafe)** — this is normal for a
  personal test app
- Click **Allow** to grant **read-only** Gmail access
- The browser shows "authentication flow completed" — close it
- A **`token.json`** file now appears in the folder

You never log in again — `token.json` refreshes itself automatically.

---

## 6. Verify everything

Run the full smoke test from the `triage-system` directory:

```powershell
uv run --no-project --with-requirements requirements.txt python scripts/smoke_test.py
```

Expected:

```
[ PASS ] config — all keys present
[ PASS ] database — tables initialized
[ PASS ] telegram — message sent (check your chat)
[ PASS ] llm router — GEMINI responded
[ PASS ] classifier — returned a structured result
[ PASS ] gmail — auth OK, fetch OK
RESULT: 6/6 checks passed
```

If any line shows `[ FAIL ]`, read the error printed next to it and see
the troubleshooting table below.

---

## 7. Run the agent

```powershell
uv run --no-project --with-requirements requirements.txt python main.py
```

- Polls Gmail immediately, then every 5 minutes
- HIGH-priority emails → instant Telegram alert
- LOW-priority emails → batched into a digest sent daily at `DIGEST_HOUR`
- Press **Ctrl+C** to stop

---

## Troubleshooting

| Symptom | Cause / Fix |
|---------|-------------|
| `Python was not found` | Use `uv run ...` (as shown), or activate the venv |
| OAuth: "access blocked" / "app not verified" | You skipped §5d — add your Gmail as a test user |
| OAuth: browser warning "Google hasn't verified this app" | Normal — click Advanced → Go to email-triage (unsafe) |
| `credentials.json` not found | File missing or misnamed — see §5e step 5–6 |
| Telegram check fails, returns False | Wrong bot token, or you didn't message the bot first (§4b) |
| Telegram 400 "chat not found" | Wrong `TELEGRAM_CHAT_ID` |
| `RouterExhaustedException` | Both API keys invalid/empty — recheck §2 and §3 |
| Gemini 404 model not found | The `GEMINI_MODEL` value isn't available on your key — set a different free model in `.env` (e.g. `GEMINI_MODEL=gemini-2.0-flash`) |
| `RefreshError: invalid_grant` | `token.json` expired/revoked — delete it and redo §5f |

---

## Files you end up with

| File | Created by | Committed to git? |
|------|-----------|-------------------|
| `.env` | You (this guide) | ❌ No — gitignored |
| `credentials.json` | Google Cloud download (§5e) | ❌ No — gitignored |
| `token.json` | First OAuth login (§5f) | ❌ No — gitignored |
| `triage.db` | First run | ❌ No — gitignored |

All four contain secrets or local state and are intentionally excluded from
git. Keep it that way.
