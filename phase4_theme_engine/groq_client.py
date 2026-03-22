"""
Phase 4 — Groq API Client

A thin wrapper around the Groq SDK with retry logic.
Supports extracting rate-limit headers for the MCP router.
"""

import time
import logging
from groq import Groq, GroqError

logger = logging.getLogger(__name__)


class GroqClient:
    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        self.client = Groq(api_key=api_key)
        self.model = model
        # Latest rate-limit info from response headers
        self.last_remaining_tokens = None
        self.last_used_tokens = None

    def chat_completion(self, system_prompt: str, user_prompt: str, retries: int = 3) -> str:
        """
        Send a chat completion request to Groq with retries.
        Also updates rate-limit token tracking from response headers.
        """
        for attempt in range(retries):
            try:
                # Use with_raw_response to access HTTP headers
                raw_response = self.client.chat.completions.with_raw_response.create(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    model=self.model,
                    temperature=0.1,
                    response_format={"type": "json_object"} if "json" in system_prompt.lower() else None
                )

                # Extract rate-limit headers
                headers = raw_response.headers
                remaining = headers.get("x-ratelimit-remaining-tokens")
                if remaining is not None:
                    self.last_remaining_tokens = int(remaining)
                used = headers.get("x-ratelimit-used-tokens")
                if used is not None:
                    self.last_used_tokens = int(used)

                # Parse the completion response
                completion = raw_response.parse()
                content = completion.choices[0].message.content
                return content if content is not None else ""


            except GroqError as e:
                # Check if it's a rate limit error — expose for MCP router
                if "rate_limit" in str(e).lower() or "429" in str(e):
                    self.last_remaining_tokens = 0

                if attempt == retries - 1:
                    raise e
                wait = 2 ** attempt
                logger.warning(f"Groq API error on attempt {attempt + 1}: {e}. Retrying in {wait}s...")
                time.sleep(wait)
        return ""
