"""
llm_client.py
=============
Thin wrapper around the llm7.io OpenAI-compatible REST API.

llm7.io exposes the standard OpenAI `/v1/chat/completions` endpoint and
accepts *any* string as an API key — pass ``"unused"`` (the default) and it
just works without registration.
"""

from __future__ import annotations

import os
import time
import logging
from typing import Optional

from openai import OpenAI, APIStatusError, APIConnectionError

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "https://api.llm7.io/v1"
_DEFAULT_MODEL = "gpt-4o-mini"
_DEFAULT_KEY = "unused"


class LLMClient:
    """OpenAI-compatible client pointed at llm7.io."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        max_retries: int = 3,
        retry_backoff: float = 1.5,
    ) -> None:
        self.api_key = api_key or os.getenv("LLM_API_KEY", _DEFAULT_KEY)
        self.base_url = base_url or os.getenv("LLM_API_BASE_URL", _DEFAULT_BASE_URL)
        self.model = model or os.getenv("LLM_MODEL", _DEFAULT_MODEL)
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff

        self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def complete(self, system_prompt: str, user_message: str) -> str:
        """Send a chat completion request and return the assistant's reply.

        Retries on transient server errors (5xx / connection issues) with
        exponential backoff.
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        last_exc: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.2,
                )
                return response.choices[0].message.content.strip()

            except APIStatusError as exc:
                if exc.status_code < 500:
                    # Client-side error — do not retry
                    raise
                logger.warning(
                    "llm7.io returned %s on attempt %d/%d — retrying in %.1fs",
                    exc.status_code,
                    attempt,
                    self.max_retries,
                    self.retry_backoff * attempt,
                )
                last_exc = exc

            except APIConnectionError as exc:
                logger.warning(
                    "Connection error on attempt %d/%d — retrying in %.1fs",
                    attempt,
                    self.max_retries,
                    self.retry_backoff * attempt,
                )
                last_exc = exc

            time.sleep(self.retry_backoff * attempt)

        raise RuntimeError(
            f"LLM request failed after {self.max_retries} attempts."
        ) from last_exc
