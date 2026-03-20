from __future__ import annotations

import anthropic


def generate_note(
    system: str,
    user_message: str,
    model: str = "claude-sonnet-4-6",
) -> str:
    client = anthropic.Anthropic()
    response = client.messages.create(
        model=model,
        max_tokens=2000,
        temperature=0.2,
        system=system,
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text
