# Test Emails

Ten sample emails for exercising the triage agent. Copy the **Subject** and
**Body** into Gmail and send them to the inbox the agent watches.

## How to use

1. Compose a new email in Gmail (you can send to your own address).
2. Paste the Subject and Body from one entry below.
3. Send. Leave it **unread** in the INBOX.
4. Run the agent (`python main.py`) or wait for the next poll.
5. Compare the result against the **Expected** column.

> Note: when you send to yourself, the `SENDER` header is your own address.
> Classification is driven mainly by subject + body, so this is fine — but if
> you want a realistic `SENDER`, send from a different account or ask someone
> to send a couple for you.

| # | Category | Expected priority |
|---|----------|-------------------|
| 1 | JOB | HIGH |
| 2 | FINANCIAL | HIGH |
| 3 | DEADLINE | HIGH |
| 4 | OTP_SECURITY | HIGH |
| 5 | OTP_SECURITY (phishing) | HIGH — SECURITY_ALERT |
| 6 | NEWSLETTER | LOW |
| 7 | SOCIAL | LOW |
| 8 | PERSONAL | LOW |
| 9 | FINANCIAL (informational) | LOW |
| 10 | UNKNOWN / ambiguous | HIGH (safe default) |

---

## 1 — JOB (expected: HIGH)

**Subject:** Interview Invitation — Senior Python Engineer at Nimbus Labs

**Body:**
```
Hi,

Thank you for applying to the Senior Python Engineer role at Nimbus Labs.
We were impressed with your background and would like to invite you to a
technical interview.

Please confirm your availability for either Thursday or Friday this week
between 10:00 AM and 4:00 PM. The interview will run for about 60 minutes
over Google Meet.

Kindly reply to this email with your preferred slot by end of day tomorrow
so we can send the calendar invite.

Best regards,
Priya Nair
Talent Acquisition, Nimbus Labs
```

---

## 2 — FINANCIAL (expected: HIGH)

**Subject:** Action Required: Credit Card Payment Due in 2 Days

**Body:**
```
Dear Customer,

This is a reminder that the minimum payment for your HDFC credit card
ending 4471 is due on 24 May 2026.

Total amount due: ₹18,450.00
Minimum amount due: ₹1,850.00
Due date: 24 May 2026

To avoid a late payment fee of ₹500 and interest charges, please make the
payment before the due date. You can pay through net banking, UPI, or the
mobile app.

If you have already paid, please ignore this message.

HDFC Bank Cards
```

---

## 3 — DEADLINE (expected: HIGH)

**Subject:** Final Reminder: Scholarship Form Submission Closes Tomorrow

**Body:**
```
Dear Applicant,

This is the final reminder that the National Merit Scholarship application
portal closes tomorrow, 23 May 2026, at 11:59 PM IST.

Our records show your application is still INCOMPLETE — the income
certificate and the signed declaration form have not been uploaded.

Applications that remain incomplete after the deadline will not be
considered, and no extension will be granted.

Please log in to the portal and complete your submission as soon as
possible.

Scholarship Cell
```

---

## 4 — OTP_SECURITY (expected: HIGH)

**Subject:** New sign-in to your account from a new device

**Body:**
```
Hi,

We noticed a new sign-in to your account.

Device: Windows PC
Browser: Chrome
Location: Mumbai, India
Time: 22 May 2026, 4:12 PM IST

If this was you, no action is needed.

If you do NOT recognise this activity, your account may be compromised.
Please reset your password immediately and review your recent activity.

Account Security Team
```

---

## 5 — OTP_SECURITY / phishing (expected: HIGH — SECURITY_ALERT)

**Subject:** URGENT!! Your account will be DELETED — verify now

**Body:**
```
Dear user,

Our system has detected unusual activity. Your account has been LOCKED and
will be permanently DELETED within 24 hours unless you verify immediately.

Click the link below and enter your username, password, and OTP to restore
access right now:

http://account-verify-security-update.example-login.ru/restore

Failure to act will result in permanent loss of all your data.

This is your final warning.

Security Department
```

---

## 6 — NEWSLETTER (expected: LOW)

**Subject:** Acme Weekly — 5 new dashboard features you might have missed

**Body:**
```
Hello,

Here's what's new at Acme this week:

• Custom dashboard layouts — drag and drop any widget
• Dark mode is now available on mobile
• Faster CSV exports, up to 3x quicker on large datasets
• New integration with Slack for alerts
• A refreshed help center with video walkthroughs

Read the full changelog on our blog. As always, reply to this email if you
have feedback — we love hearing from you.

Happy building,
The Acme Team

Unsubscribe | Manage preferences
```

---

## 7 — SOCIAL (expected: LOW)

**Subject:** You have 4 new notifications this week

**Body:**
```
Hi there,

Here's a summary of your network activity:

• Rahul Mehta and 2 others viewed your profile
• Your comment received 12 reactions
• 3 new posts from people you follow
• A job you might be interested in was posted

Open the app to catch up.

See you online,
LinkedIn
```

---

## 8 — PERSONAL (expected: LOW)

**Subject:** Photos from last weekend's trip

**Body:**
```
Hey!

Finally got around to sorting the photos from the Lonavala trip — they
came out really well. I've put them all in a shared album, link below
whenever you get a chance to look.

No rush at all. Also, are you free sometime next month? Was thinking we
could plan another short trip, maybe Coorg this time.

Talk soon,
Arjun
```

---

## 9 — FINANCIAL / informational (expected: LOW)

**Subject:** Your monthly account statement is ready

**Body:**
```
Dear Customer,

Your account statement for April 2026 is now available to view and
download in net banking and the mobile app.

This is an informational message only — no action is required. Your
statement includes a summary of all transactions, interest earned, and
your closing balance for the period.

For security reasons, statements are not attached to email. Please log in
to view yours.

Thank you for banking with us.
State Bank
```

---

## 10 — UNKNOWN / ambiguous (expected: HIGH — safe default)

**Subject:** Re: following up

**Body:**
```
Hi,

Just circling back on the thing we discussed. Let me know what you think
when you get a moment — happy to jump on a quick call if that's easier.

Thanks
```

---

## What to check after sending

- **HIGH** emails (#1–5, #10) → you should get an instant Telegram alert each,
  with the category and provider in the footer.
- **LOW** emails (#6–9) → no instant alert; they go into the digest queue and
  appear in the daily digest at `DIGEST_HOUR`.
- To force the digest immediately without waiting, you can flush it manually:
  ```powershell
  uv run --no-project --with-requirements requirements.txt python -c "from pipeline import digest; print('sent:', digest.flush_digest())"
  ```
- #5 (phishing) should come back HIGH with `SECURITY_ALERT` noted in the
  message text.
- #10 is deliberately vague — the agent should default it to HIGH and flag it
  as ambiguous in `step4_self_check`.
```
