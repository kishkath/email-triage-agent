from typing import Optional

from openai import OpenAI
from pydantic import BaseModel

from core.config import OPENAI_API_KEY, OPENAI_MODEL
from .base import LLMProvider


class OpenAIProvider(LLMProvider):
    name = "OPENAI"

    def __init__(self):
        if not OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY not set")
        self._client = OpenAI(api_key=OPENAI_API_KEY)
        self._model = OPENAI_MODEL

    def complete(
        self,
        system_prompt: str,
        user_message: str,
        response_schema: Optional[type[BaseModel]] = None,
    ) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        if response_schema is not None:
            resp = self._client.beta.chat.completions.parse(
                model=self._model,
                messages=messages,
                temperature=0.2,
                max_tokens=800,
                response_format=response_schema,
            )
            message = resp.choices[0].message
            if message.refusal:
                raise RuntimeError(f"OpenAI refused: {message.refusal}")
            text = message.content
        else:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=0.2,
                max_tokens=800,
                response_format={"type": "json_object"},
            )
            text = resp.choices[0].message.content

        if not text:
            raise RuntimeError("Empty response from OpenAI")
        return text
