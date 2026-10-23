"""The one and only model used by this project.

THE RULE
--------
Every agent here runs `gpt-6-luna` through Portkey. Nothing else, ever,
including as a fallback when something fails. Points are deducted if another
model appears in the code or runs.

Every agent is built from `build_model()` below, so there is exactly one place
a model name can enter the system, and that place reads it from
`app/config.py`. No agent file names a model. `scripts/check_model_guard.py`
scans the repo for stray identifiers as a second line of defence.

TWO GOTCHAS THAT COST REAL TIME (carried over from Homework 5)
--------------------------------------------------------------
1. `max_tokens` is rejected by this model family -- it wants
   `max_completion_tokens`, and sending the wrong one gets a confusing HTTP 400
   from the Azure backend behind Portkey.

2. pydantic-ai infers a reasoning profile from the `gpt-` prefix and sends
   `reasoning_effort`. Azure rejects that in combination with function tools:

       Function tools with reasoning_effort are not supported for
       gpt-6-luna-global in /v1/chat/completions.

   So `openai_reasoning_effort` is pinned to 'none'.
"""

from __future__ import annotations

import os

from openai import AsyncOpenAI
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIChatModelSettings
from pydantic_ai.providers.openai import OpenAIProvider

from app.config import MODEL, PORTKEY_BASE_URL, portkey_api_key

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

# A single HTTP timeout so one stalled call cannot hang a whole run.
REQUEST_TIMEOUT_S = 90.0
MAX_HTTP_RETRIES = 1


def _assert_single_model(name: str) -> None:
    """Fail loudly if anything other than the permitted model is requested."""
    if name != MODEL:
        raise RuntimeError(
            f"Refusing to build a model named {name!r}. This project is permitted "
            f"exactly one model: {MODEL!r}. See backend/model_provider.py."
        )


def build_model() -> OpenAIChatModel:
    """Return the shared model object. Every agent uses this."""
    _assert_single_model(MODEL)

    client = AsyncOpenAI(
        base_url=PORTKEY_BASE_URL,
        api_key=portkey_api_key(),
        timeout=REQUEST_TIMEOUT_S,
        max_retries=MAX_HTTP_RETRIES,
    )
    return OpenAIChatModel(
        MODEL,
        provider=OpenAIProvider(openai_client=client),
        settings=OpenAIChatModelSettings(openai_reasoning_effort="none"),
    )


def model_name() -> str:
    """The model identifier, for the audit trail."""
    return MODEL
