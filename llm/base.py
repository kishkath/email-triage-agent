from abc import ABC, abstractmethod
from typing import Optional

from pydantic import BaseModel


class LLMProvider(ABC):
    name: str = "BASE"

    @abstractmethod
    def complete(
        self,
        system_prompt: str,
        user_message: str,
        response_schema: Optional[type[BaseModel]] = None,
    ) -> str:
        """Return raw JSON text. If response_schema is given, constrain the
        model to emit conformant JSON. Raise on any failure."""
