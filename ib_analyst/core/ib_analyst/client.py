"""client.py — Thin wrapper around the Anthropic messages API for note generation."""
from __future__ import annotations

import logging

import anthropic

logger = logging.getLogger(__name__)


def generate_note(
    system: str,
    user_message: str,
    model: str = "claude-sonnet-4-6",
) -> str:
    """Call the Claude API and return the generated analyst note text.

    Args:
        system:       System prompt defining the analyst persona and instructions.
        user_message: User message containing company context and financial data.
        model:        Claude model identifier.

    Returns:
        The raw text of the first content block in the API response.

    Raises:
        anthropic.APIError: On network or API-level failures.
    """
    logger.debug("Calling Claude API: model=%s, prompt_chars=%d", model, len(user_message))
    client = anthropic.Anthropic()
    response = client.messages.create(
        model=model,
        max_tokens=2000,
        temperature=0.2,
        system=system,
        messages=[{"role": "user", "content": user_message}],
    )
    logger.debug("Claude API response: stop_reason=%s", response.stop_reason)
    return response.content[0].text
