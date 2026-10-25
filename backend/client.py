"""One place where a model call actually happens.

Every agent calls `call_json()`. That gives the project a single point for:
  * the cached rubric prefix (always message 0, always identical),
  * token accounting into the run ledger,
  * the spend cap,
  * the reasoning_effort pin this model family needs,
  * JSON parsing and one repair attempt.

Structured output is requested as a JSON object with the schema spelled out in
the prompt, then validated with pydantic, rather than using a provider-specific
structured-output parameter. Portkey sits between us and the backend and does
not reliably pass those through, and a schema in the prompt works everywhere.
"""

from __future__ import annotations

import json
import time
from typing import TypeVar

from openai import OpenAI
from pydantic import BaseModel, ValidationError

from app.config import (
    MAX_COMPLETION_TOKENS,
    MODEL,
    PORTKEY_BASE_URL,
    portkey_api_key,
)
from backend.rubric import static_prefix
from backend.usage import Ledger

T = TypeVar("T", bound=BaseModel)

REQUEST_TIMEOUT_S = 90.0
_client: OpenAI | None = None


class ContentFiltered(RuntimeError):
    """The provider's content filter refused the request.

    Seen on a perfectly ordinary handwritten composition about a student's
    family. The filter sits between us and the model and will occasionally
    refuse real student work, so this is a condition the app has to survive
    and explain rather than a crash. Callers that have an alternative to try
    -- a different page rotation, for instance -- can catch this and move on.
    """


def _as_filtered(exc: Exception) -> Exception:
    text = str(exc)
    if "content_filter" in text or "content management policy" in text:
        return ContentFiltered(
            "The provider's content filter refused this image or text. This "
            "can happen on legitimate student work; it is a provider policy "
            "decision, not a judgement about the composition."
        )
    return exc


def client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            base_url=PORTKEY_BASE_URL,
            api_key=portkey_api_key(),
            timeout=REQUEST_TIMEOUT_S,
            max_retries=1,
        )
    return _client


def _schema_block(model_cls: type[BaseModel]) -> str:
    return (
        "Reply with a single JSON object and nothing else. It must validate "
        "against this JSON Schema:\n"
        + json.dumps(model_cls.model_json_schema(), indent=2)
    )


def call_json(
    *,
    agent: str,
    task: str,
    out_model: type[T],
    ledger: Ledger,
    user_content: list[dict] | str | None = None,
) -> T:
    """Run one agent turn and return a validated object.

    Message layout matters. Message 0 is the rubric prefix and never varies --
    that is the cached region. Everything specific to this agent or this
    student goes in later messages. See backend/rubric.py.
    """
    ledger.check_budget()

    content: list[dict]
    if user_content is None:
        content = [{"type": "text", "text": task}]
    elif isinstance(user_content, str):
        content = [{"type": "text", "text": task + "\n\n" + user_content}]
    else:
        content = [{"type": "text", "text": task}, *user_content]

    messages = [
        {"role": "system", "content": static_prefix()},
        {"role": "system", "content": _schema_block(out_model)},
        {"role": "user", "content": content},
    ]

    def _once(extra: str | None = None) -> tuple[str, object]:
        msgs = messages if extra is None else [*messages, {"role": "user", "content": extra}]
        started = time.time()
        try:
            resp = client().chat.completions.create(
                model=MODEL,
                messages=msgs,
                max_completion_tokens=MAX_COMPLETION_TOKENS,
                reasoning_effort="none",
                response_format={"type": "json_object"},
            )
        except Exception as exc:  # noqa: BLE001 -- re-raised, possibly retyped
            raise _as_filtered(exc) from exc
        ledger.record(agent, resp.model, resp.usage, time.time() - started)
        return (resp.choices[0].message.content or "").strip(), resp

    raw, _ = _once()
    try:
        return out_model.model_validate_json(raw)
    except (ValidationError, ValueError) as first_error:
        # One repair attempt. Cheaper than failing a whole run, and the
        # ledger records it so a flaky agent shows up in the cost table.
        raw2, _ = _once(
            "Your previous reply did not validate against the schema:\n"
            f"{first_error}\n\nPrevious reply:\n{raw}\n\n"
            "Reply again with ONLY the corrected JSON object."
        )
        return out_model.model_validate_json(raw2)
