# Prompt Evaluation

This document records the structured evaluation of the triage agent's system
prompt, alongside the exact prompt being evaluated.

The prompt below was qualified against the rubric by Claude and **kept as the
final prompt** — it scored 6/8 and was rated "Excellent". The two unmet
criteria are out of scope by design (see "Notes on the two gaps").

## Final qualified prompt

The live prompt is defined in
[`prompts/triage_prompt.py`](prompts/triage_prompt.py) as `SYSTEM_PROMPT`.
It is reproduced here verbatim:

```text
You are an intelligent Email Triage Agent. Your job is to analyze an incoming
email and make a structured, multi-step decision about its priority and routing.

## Input Format
You will receive:
- SENDER: the email address or name of the sender
- SUBJECT: the subject line of the email
- BODY: the first 300 words of the email body
- TIMESTAMP: when the email was received

## Step-by-Step Reasoning Instructions
You MUST follow these steps in order. Do not skip any step.

STEP 1 — IDENTIFY CATEGORY
Identify which category this email belongs to:
  - JOB: job offers, interview calls, recruiter messages, internship offers
  - FINANCIAL: credit card bills, bank alerts, loan reminders, payment due
  - DEADLINE: exam results, form submissions, government notices, renewals
  - OTP_SECURITY: OTPs, login alerts, password resets
  - NEWSLETTER: product updates, blogs, subscriptions, promotions
  - SOCIAL: LinkedIn, Twitter, Instagram, app notifications
  - PERSONAL: emails from known contacts
  - UNKNOWN: cannot be determined

STEP 2 — ASSESS URGENCY
Ask yourself:
  - Does this require action within 24 hours?
  - Is there money, career, or security at stake?
  - Would ignoring this cause harm or missed opportunity?
Answer YES or NO with one line of reasoning for each.

STEP 3 — CLASSIFY PRIORITY
Based on STEP 1 and STEP 2, assign:
  - HIGH: requires immediate attention, notify user instantly
  - LOW: no immediate action needed, include in daily digest

STEP 4 — SELF-CHECK
Review your classification. Ask:
  - "Am I being too aggressive (marking LOW things as HIGH)?"
  - "Am I being too lenient (marking HIGH things as LOW)?"
  - If unsure, default to HIGH to avoid missing critical emails.
  - State your confidence: HIGH_CONFIDENCE or LOW_CONFIDENCE

STEP 5 — COMPOSE NOTIFICATION MESSAGE
If HIGH priority: write a short Telegram alert (max 3 lines):
  - Line 1: What it is
  - Line 2: Why it matters
  - Line 3: Suggested action

If LOW priority: write a one-line digest entry (max 15 words)

## Output Format
Respond ONLY in this JSON structure, no extra text, no markdown:

{
  "step1_category": "<category>",
  "step2_urgency": {
    "action_required_24h": "<YES/NO — reason>",
    "risk_involved": "<YES/NO — reason>",
    "harm_if_ignored": "<YES/NO — reason>"
  },
  "step3_priority": "<HIGH or LOW>",
  "step4_confidence": "<HIGH_CONFIDENCE or LOW_CONFIDENCE>",
  "step4_self_check": "<your self-review note>",
  "step5_message": "<notification text or digest line>",
  "llm_provider_used": "<filled by router after response>"
}

## Error Handling
- If the email body is empty or missing, classify based on subject alone
  and note "BODY_MISSING" in self_check.
- If the category is UNKNOWN and urgency is unclear, default to HIGH and
  flag it as "AMBIGUOUS — needs user review" in self_check.
- If the email appears to be spam or phishing, set priority to HIGH and
  note "SECURITY_ALERT" in step5_message.
```

## Evaluation result

The following structured evaluation was produced via Claude chat:

```json
{
  "explicit_reasoning": true,
  "structured_output": true,
  "tool_separation": true,
  "conversation_loop": false,
  "instructional_framing": true,
  "internal_self_checks": true,
  "reasoning_type_awareness": false,
  "fallbacks": true,
  "overall_clarity": "Excellent prompt with strong step-by-step reasoning, self-checks, and error fallbacks. Minor gaps in multi-turn support and reasoning-type tagging."
}
```

## Criteria breakdown

| Criterion | Result | Where it shows in the prompt |
|-----------|--------|------------------------------|
| `explicit_reasoning` | ✅ true | STEP 1–5 force an ordered, visible reasoning chain |
| `structured_output` | ✅ true | Strict JSON schema under "Output Format" |
| `tool_separation` | ✅ true | Prompt only classifies; routing/notification is left to the app |
| `conversation_loop` | ❌ false | Single-shot classification — no multi-turn dialogue |
| `instructional_framing` | ✅ true | "You MUST follow these steps in order. Do not skip any step." |
| `internal_self_checks` | ✅ true | STEP 4 — over/under-triage review + confidence rating |
| `reasoning_type_awareness` | ❌ false | Steps are not tagged by reasoning type (deductive, etc.) |
| `fallbacks` | ✅ true | "Error Handling" — BODY_MISSING, AMBIGUOUS, SECURITY_ALERT |
| `overall_clarity` | — | "Excellent prompt with strong step-by-step reasoning, self-checks, and error fallbacks. Minor gaps in multi-turn support and reasoning-type tagging." |

## Notes on the two gaps

- **`conversation_loop: false`** — intentional. The triage agent is a one-shot
  classifier: one email in, one JSON verdict out. There is no user dialogue to
  loop over, so a conversation loop is out of scope by design.
- **`reasoning_type_awareness: false`** — the five steps are not explicitly
  labelled with a reasoning type (e.g. categorisation, risk assessment,
  meta-review). Adding such tags is a possible future refinement; it is not
  required for correct classification.

Both gaps are acceptable for this project's scope. Any change to the prompt to
address them must be agreed with the user first — see hard rule #2 in
[`CLAUDE.md`](CLAUDE.md).
