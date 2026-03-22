"""
Phase 4 — LLM MCP Router

Internal MCP-based token-aware routing layer for LLM calls.
Tracks Groq's remaining token quota via response headers and
proactively routes to OpenRouter when Groq is low or exhausted.
"""

import logging

logger = logging.getLogger(__name__)


class LLMMCPRouter:
    """
    MCP-based LLM router that intelligently selects between
    Groq and OpenRouter based on token availability.
    """

    def __init__(self, openrouter_client, groq_client, groq_daily_limit: int = 100_000):
        self.openrouter = openrouter_client
        self.groq = groq_client
        self._groq_daily_limit = groq_daily_limit
        self._token_threshold = 10_000  # Switch to OpenRouter when Groq has < this many tokens
        self._groq_remaining = groq_daily_limit  # Assume full at start
        self._calls_made = 0
        self._groq_calls = 0
        self._openrouter_calls = 0

    def get_token_status(self) -> dict:
        """
        Returns current token availability and routing info.
        Useful for observability and logging.
        """
        return {
            "groq_remaining": self._groq_remaining,
            "groq_daily_limit": self._groq_daily_limit,
            "threshold": self._token_threshold,
            "active_provider": self._pick_provider(),
            "calls_made": self._calls_made,
            "groq_calls": self._groq_calls,
            "openrouter_calls": self._openrouter_calls,
        }

    def _pick_provider(self) -> str:
        """Decide which provider to use. Primary is now OpenRouter."""
        return "openrouter"

    def _update_groq_state(self):
        """Read latest rate-limit info from the Groq client's cached headers."""
        if self.groq.last_remaining_tokens is not None:
            self._groq_remaining = self.groq.last_remaining_tokens

    def chat_completion(self, system_prompt: str, user_prompt: str) -> str:
        """
        Routes to best provider.

        1. Try OpenRouter (Primary)
        2. If OpenRouter fails → Fallback to Groq
        """
        self._calls_made += 1
        
        try:
            # Primary: OpenRouter
            logger.info("MCP Router: Using OpenRouter (Primary)")
            print("      🔌 MCP Router → OpenRouter (Primary)")
            result = self.openrouter.chat_completion(system_prompt, user_prompt)
            self._openrouter_calls += 1
            return result
        except Exception as e:
            # Fallback: Groq
            logger.warning(f"MCP Router: OpenRouter failed ({e}), falling back to Groq")
            print("      ⚠️  OpenRouter failed — switching to Groq")
            
            logger.info(f"MCP Router: Using Groq (Fallback, remaining: ~{self._groq_remaining} tokens)")
            print(f"      🔌 MCP Router → Groq (Fallback, remaining: ~{self._groq_remaining} tokens)")
            result = self.groq.chat_completion(system_prompt, user_prompt)
            self._update_groq_state()
            self._groq_calls += 1
            return result
