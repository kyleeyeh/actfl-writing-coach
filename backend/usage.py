"""Per-call token accounting.

The report has to show input, cached input, and output tokens from real runs,
plus cost per run, per user per month, and at 100 and 10,000 users. Collecting
that after the fact is guesswork, so every model call in this project goes
through a ledger that records it at the moment it happens.

The ledger also backs the spend guardrail: a run that exceeds
MAX_REQUESTS_PER_RUN is stopped rather than allowed to loop.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path

from app.config import (
    MAX_REQUESTS_PER_RUN,
    OUTPUT_DIR,
    PRICE_PER_1M_CACHED_INPUT,
    PRICE_PER_1M_INPUT,
    PRICE_PER_1M_OUTPUT,
)


class SpendLimitExceeded(RuntimeError):
    """Raised when a run asks for more model calls than it is allowed."""


@dataclass
class CallRecord:
    agent: str
    model: str
    prompt_tokens: int
    cached_tokens: int
    completion_tokens: int
    seconds: float

    @property
    def uncached_prompt_tokens(self) -> int:
        return max(self.prompt_tokens - self.cached_tokens, 0)

    @property
    def cost_usd(self) -> float:
        return (
            self.uncached_prompt_tokens / 1_000_000 * PRICE_PER_1M_INPUT
            + self.cached_tokens / 1_000_000 * PRICE_PER_1M_CACHED_INPUT
            + self.completion_tokens / 1_000_000 * PRICE_PER_1M_OUTPUT
        )


@dataclass
class Ledger:
    """One run's worth of calls."""

    label: str = "run"
    calls: list[CallRecord] = field(default_factory=list)
    started: float = field(default_factory=time.time)

    def check_budget(self) -> None:
        if len(self.calls) >= MAX_REQUESTS_PER_RUN:
            raise SpendLimitExceeded(
                f"This run already made {len(self.calls)} model calls, the cap "
                f"is {MAX_REQUESTS_PER_RUN}. Stopping rather than spending more."
            )

    def record(self, agent: str, model: str, usage, seconds: float) -> CallRecord:
        """Record one call. `usage` is the provider's usage object."""
        cached = 0
        details = getattr(usage, "prompt_tokens_details", None)
        if details is not None:
            # Providers disagree on whether this is an object or a dict.
            cached = (
                getattr(details, "cached_tokens", None)
                if not isinstance(details, dict)
                else details.get("cached_tokens")
            ) or 0

        rec = CallRecord(
            agent=agent,
            model=model,
            prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            cached_tokens=cached,
            completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
            seconds=seconds,
        )
        self.calls.append(rec)
        return rec

    # --- totals ------------------------------------------------------------
    @property
    def prompt_tokens(self) -> int:
        return sum(c.prompt_tokens for c in self.calls)

    @property
    def cached_tokens(self) -> int:
        return sum(c.cached_tokens for c in self.calls)

    @property
    def completion_tokens(self) -> int:
        return sum(c.completion_tokens for c in self.calls)

    @property
    def cost_usd(self) -> float:
        return sum(c.cost_usd for c in self.calls)

    @property
    def cache_hit_rate(self) -> float:
        return self.cached_tokens / self.prompt_tokens if self.prompt_tokens else 0.0

    def summary(self) -> dict:
        return {
            "label": self.label,
            "calls": len(self.calls),
            "prompt_tokens": self.prompt_tokens,
            "cached_tokens": self.cached_tokens,
            "uncached_prompt_tokens": self.prompt_tokens - self.cached_tokens,
            "completion_tokens": self.completion_tokens,
            "cache_hit_rate": round(self.cache_hit_rate, 4),
            "cost_usd": round(self.cost_usd, 6),
            "wall_seconds": round(time.time() - self.started, 2),
            "per_agent": [asdict(c) | {"cost_usd": round(c.cost_usd, 6)} for c in self.calls],
        }

    def save(self, name: str) -> Path:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        path = OUTPUT_DIR / name
        path.write_text(
            json.dumps(self.summary(), indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return path

    def table(self) -> str:
        """Plain-text table, for the console and for report screenshots."""
        rows = [
            f"{'agent':<22}{'in':>8}{'cached':>8}{'out':>8}{'$':>11}{'s':>7}",
            "-" * 64,
        ]
        for c in self.calls:
            rows.append(
                f"{c.agent:<22}{c.prompt_tokens:>8}{c.cached_tokens:>8}"
                f"{c.completion_tokens:>8}{c.cost_usd:>11.6f}{c.seconds:>7.1f}"
            )
        rows.append("-" * 64)
        rows.append(
            f"{'TOTAL':<22}{self.prompt_tokens:>8}{self.cached_tokens:>8}"
            f"{self.completion_tokens:>8}{self.cost_usd:>11.6f}"
            f"{sum(c.seconds for c in self.calls):>7.1f}"
        )
        rows.append(f"cache hit rate on input: {self.cache_hit_rate:.1%}")
        return "\n".join(rows)
