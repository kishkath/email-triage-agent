import logging
import re

from pydantic import ValidationError

from core.config import LLM_PROVIDER, FALLBACK_PROVIDER
from core.schema import Category, Confidence, Priority, TriageResult, Urgency
from llm import LLMRouter, RouterExhaustedException
from prompts import SYSTEM_PROMPT, build_user_message

log = logging.getLogger(__name__)

_router: LLMRouter | None = None


def _get_router() -> LLMRouter:
    global _router
    if _router is None:
        _router = LLMRouter(primary=LLM_PROVIDER, fallback=FALLBACK_PROVIDER)
    return _router


def _strip_trailing_commas(s: str) -> str:
    # LLMs occasionally emit `,}` or `,]` which strict JSON parsers reject.
    return re.sub(r",(\s*[}\]])", r"\1", s)


def _parse_result(text: str) -> TriageResult:
    text = text.strip()
    try:
        return TriageResult.model_validate_json(text)
    except ValidationError:
        pass
    m = re.search(r"\{.*\}", text, re.DOTALL)
    blob = m.group(0) if m else text
    try:
        return TriageResult.model_validate_json(blob)
    except ValidationError:
        return TriageResult.model_validate_json(_strip_trailing_commas(blob))


def _default_high(reason: str, provider: str | None, subject: str) -> TriageResult:
    return TriageResult(
        step1_category=Category.UNKNOWN,
        step2_urgency=Urgency(
            action_required_24h="YES — error path, defaulting to HIGH",
            risk_involved="YES — may miss critical email",
            harm_if_ignored="YES — unclassified",
        ),
        step3_priority=Priority.HIGH,
        step4_confidence=Confidence.LOW_CONFIDENCE,
        step4_self_check=f"AMBIGUOUS — needs user review ({reason})",
        step5_message=f"Unclassified email needs review: {subject}",
        llm_provider_used=provider or "NONE",
    )


def classify_email(email: dict) -> TriageResult:
    router = _get_router()
    user_message = build_user_message(email)
    try:
        raw = router.complete(SYSTEM_PROMPT, user_message, response_schema=TriageResult)
    except RouterExhaustedException as e:
        log.error("Router exhausted: %s", e)
        return _default_high("router_exhausted", None, email.get("subject", ""))

    provider = router.last_provider_used
    try:
        result = _parse_result(raw)
    except ValidationError as e:
        log.error("Schema validation failed (%s): %s", e, raw[:200])
        return _default_high("parse_error", provider, email.get("subject", ""))

    result.llm_provider_used = provider or "UNKNOWN"
    return result
