"""
Phase 4 — OpenRouter API Client

A thin wrapper around the OpenRouter REST API with retry logic.
Mirrors GroqClient's interface for interchangeability.

Used for LLM Call #1 (theme generation) to bypass Groq's daily rate limit.
"""

import time
import json
import logging
import requests

logger = logging.getLogger(__name__)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"


class OpenRouterClient:
    def __init__(self, api_key: str, model: str = "liquid/lfm-2.5-1.2b-thinking:free"):
        self.api_key = api_key
        self.model = model

    def chat_completion(self, system_prompt: str, user_prompt: str, retries: int = 3, model_override: str = None) -> str:
        """
        Send a chat completion request to OpenRouter with retries.

        Same interface as GroqClient.chat_completion for interchangeability.
        """
        target_model = model_override or self.model
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/indmoney-pulse-generator",
            "X-Title": "INDMoney Pulse Generator",
        }

        payload = {
            "model": target_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
        }

        for attempt in range(retries):
            try:
                response = requests.post(
                    OPENROUTER_API_URL,
                    headers=headers,
                    json=payload,
                    timeout=60,
                )
                response.raise_for_status()

                data = response.json()

                # Check for explicit error in the JSON response
                if "error" in data:
                    error_msg = data["error"].get("message", str(data["error"]))
                    logger.warning(f"OpenRouter returned error: {error_msg}")
                    return ""

                if "choices" not in data or not data["choices"]:
                    logger.warning(f"OpenRouter response missing 'choices': {data}")
                    return ""

                content = data["choices"][0]["message"]["content"]

                if content is None:
                    logger.warning("OpenRouter returned empty content.")
                    return ""

                # LFM2.5-Thinking models may wrap output in <think>...</think> tags

                # Strip the thinking section and return only the final answer
                if "<think>" in content:
                    # Everything after </think> is the actual response
                    parts = content.split("</think>")
                    if len(parts) > 1:
                        content = parts[-1].strip()
                    else:
                        # No closing tag yet — strip opening tag prefix
                        content = content.split("<think>")[-1].strip()

                # Strip markdown code fences (```json ... ```) that some models add
                if content.startswith("```"):
                    lines = content.split("\n")
                    # Remove first line (```json) and last line (```)
                    if lines[-1].strip() == "```":
                        lines = lines[1:-1]
                    else:
                        lines = lines[1:]
                    content = "\n".join(lines).strip()

                return content

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 401:
                    raise RuntimeError("401 Unauthorized: Your OpenRouter API Key is missing or invalid. Please check your .env file or Hugging Face Secrets.")
                    
                if e.response.status_code == 402:
                    logger.warning(f"402 Payment Required for {target_model}. Automatically falling back to free tier model.")
                    print(f"      💰 Out of credits for {target_model}. Falling back to free model...")
                    target_model = "liquid/lfm-2.5-1.2b-thinking:free"
                    payload["model"] = target_model
                    continue # Try again immediately with the free model
                
                if attempt == retries - 1:
                    raise RuntimeError(f"OpenRouter API failed after {retries} attempts. Last error: {e}")
                wait = 2 ** attempt
                logger.warning(f"OpenRouter API error on attempt {attempt + 1}: {e}. Retrying in {wait}s...")
                time.sleep(wait)

            except (requests.RequestException, KeyError, IndexError) as e:
                if attempt == retries - 1:
                    raise RuntimeError(
                        f"OpenRouter API failed after {retries} attempts. Last error: {e}"
                    )
                wait = 2 ** attempt
                logger.warning(
                    f"OpenRouter API error on attempt {attempt + 1}: {e}. Retrying in {wait}s..."
                )
                time.sleep(wait)

        return ""
