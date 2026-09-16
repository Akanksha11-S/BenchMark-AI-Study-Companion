"""Thin wrapper around the model provider.

Everything else in the app calls `ask()` and never touches the SDK
directly — swapping providers (e.g. to OpenAI, or a local open-source
model via Ollama) means editing only this file.
"""

import os
import json
import re

from google import genai
from google.genai import types

_client = None

# Pick any current Gemini model here. gemini-3.6-flash is a solid,
# inexpensive default; swap in "gemini-3.8-flash" for the newest/strongest
# Flash tier, or "gemini-3.1-pro" for the hardest reasoning tasks.
_MODEL = "gemini-3.6-flash"

# Gemini 3-series models are "thinking" models: max_output_tokens caps
# thinking tokens + visible output tokens *combined*, and thinking defaults
# to a high effort level. Short conversational replies (Learn) usually
# survive a small budget, but anything that has to follow a strict output
# format (quiz JSON, SQL JSON) can burn the whole budget on reasoning and
# come back with an empty response. Turning thinking down and giving more
# headroom fixes that.
_DEFAULT_MAX_TOKENS = 2048
_THINKING_LEVEL = "low"  # "minimal" | "low" | "high" (Flash models also allow "minimal")


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Copy .env.example to .env and add your key."
            )
        _client = genai.Client(api_key=api_key)
    return _client


def ask(system: str, user_prompt: str, max_tokens: int = _DEFAULT_MAX_TOKENS) -> str:
    """Send a single-turn request and return the model's text reply."""
    client = _get_client()
    response = client.models.generate_content(
        model=_MODEL,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=max_tokens,
            # Gemini 3 models use thinking_level, not the older thinking_budget.
            # Passing both raises an error, so only set one.
            thinking_config=types.ThinkingConfig(thinking_level=_THINKING_LEVEL),
        ),
    )
    text = (response.text or "").strip()
    if not text:
        finish_reason = None
        try:
            finish_reason = response.candidates[0].finish_reason
        except (AttributeError, IndexError, TypeError):
            pass

        if str(finish_reason) == "MAX_TOKENS" or "MAX_TOKENS" in str(finish_reason or ""):
            raise RuntimeError(
                "Model hit the token limit before producing any visible output "
                "(likely spent the budget on internal reasoning). Try raising "
                "max_tokens or lowering thinking_level further."
            )
        raise RuntimeError(f"Model returned an empty response (finish_reason={finish_reason})")
    return text


def ask_json(system: str, user_prompt: str, max_tokens: int = _DEFAULT_MAX_TOKENS) -> dict:
    """Same as ask(), but strips markdown fences and parses the result as JSON.
    Raises ValueError if the model didn't return valid JSON."""
    raw = ask(system, user_prompt, max_tokens=max_tokens)
    cleaned = re.sub(r"```json|```", "", raw).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model did not return valid JSON: {exc}\nRaw output: {raw[:500]}")