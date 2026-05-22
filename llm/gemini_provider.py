from typing import Optional

from google import genai
from google.genai import types
from pydantic import BaseModel

from core.config import GEMINI_API_KEY, GEMINI_MODEL
from .base import LLMProvider


class GeminiProvider(LLMProvider):
    name = "GEMINI"

    def __init__(self):
        if not GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY not set")
        self._client = genai.Client(api_key=GEMINI_API_KEY)
        self._model = GEMINI_MODEL

    def complete(
        self,
        system_prompt: str,
        user_message: str,
        response_schema: Optional[type[BaseModel]] = None,
    ) -> str:
        config_kwargs: dict = {
            "system_instruction": system_prompt,
            "response_mime_type": "application/json",
        }
        if response_schema is not None:
            config_kwargs["response_schema"] = response_schema

        resp = self._client.models.generate_content(
            model=self._model,
            contents=user_message,
            config=types.GenerateContentConfig(**config_kwargs),
        )
        text = resp.text
        if not text:
            raise RuntimeError("Empty response from Gemini")
        return text
