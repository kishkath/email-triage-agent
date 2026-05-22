"""Pydantic schema for the LLM triage output.

This model is the contract for STEP 1-5 of the triage prompt. It is used both
to validate raw LLM responses and as the provider-native response schema
(Gemini `response_schema`, OpenAI structured outputs) so the model is
constrained to emit conformant JSON at generation time.
"""

from enum import StrEnum

from pydantic import BaseModel


class Category(StrEnum):
    JOB = "JOB"
    FINANCIAL = "FINANCIAL"
    DEADLINE = "DEADLINE"
    OTP_SECURITY = "OTP_SECURITY"
    NEWSLETTER = "NEWSLETTER"
    SOCIAL = "SOCIAL"
    PERSONAL = "PERSONAL"
    UNKNOWN = "UNKNOWN"


class Priority(StrEnum):
    HIGH = "HIGH"
    LOW = "LOW"


class Confidence(StrEnum):
    HIGH_CONFIDENCE = "HIGH_CONFIDENCE"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"


class Urgency(BaseModel):
    action_required_24h: str
    risk_involved: str
    harm_if_ignored: str


class TriageResult(BaseModel):
    step1_category: Category
    step2_urgency: Urgency
    step3_priority: Priority
    step4_confidence: Confidence
    step4_self_check: str
    step5_message: str
    # Required (no default): a `default` key in the JSON schema is rejected by
    # Gemini's response_schema converter. The model emits a placeholder per the
    # prompt; the classifier overwrites it with the actual provider.
    llm_provider_used: str
