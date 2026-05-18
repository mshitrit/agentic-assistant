"""Shared Google Cloud Vertex AI client and single-turn completion."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import anthropic

from config.settings import GCP_PROJECT, GCP_REGION


@dataclass
class AgentResult:
    response: Optional[str] = None
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None


def get_vertex_client() -> anthropic.AnthropicVertex:
    return anthropic.AnthropicVertex(project_id=GCP_PROJECT, region=GCP_REGION)


def extract_response_text(response: anthropic.types.Message) -> str:
    text_blocks = [b.text for b in response.content if hasattr(b, "text") and b.text]
    return "\n".join(text_blocks)


def complete_single_turn(
    prompt: str,
    *,
    max_tokens: int = 1024,
    model: str = "claude-opus-4-5",
) -> AgentResult:
    if not prompt.strip():
        return AgentResult(error="empty_prompt")

    try:
        client = get_vertex_client()
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.RateLimitError as e:
        return AgentResult(error=f"rate_limit: {e}")
    except anthropic.APIError as e:
        return AgentResult(error=f"api_error: {e}")
    except Exception as e:
        return AgentResult(error=f"api_error: {e}")

    text = extract_response_text(response)
    if not text:
        return AgentResult(error="empty_response")
    return AgentResult(response=text)
