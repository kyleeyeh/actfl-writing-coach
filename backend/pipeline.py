"""Orchestration, and the run trace the report is built from.

Every stage appends a `TraceStep`. That trace is what the UI renders and what
gets screenshotted for the "one real run traced step by step" section of the
report, so it records inputs, outputs, tokens and timing per agent rather than
just the final answer.

TWO ENTRY POINTS, ON PURPOSE
----------------------------
`transcribe_step()` and `assess_step()` are separate because a human has to be
able to read and fix the transcript before anything is graded on it. That is
not a UI nicety. Measured on the dev fixtures, the transcriber turned
"entonces" into "entonses", and the Accuracy evaluator then cited the
misreading as a student spelling error -- a fabricated error, invented by OCR
and graded as if real. The confirm step is the defence against that, so the
pipeline is shaped to make skipping it the unusual path.

`run()` composes both and is what the CLI and the tests use.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

from backend import agents, guardrails
from backend.schemas import CriterionFinding, DrillSet, Placement, Transcription
from backend.usage import Ledger

CRITERIA = ("F", "A", "C", "T")


@dataclass
class TraceStep:
    agent: str
    summary: str
    detail: Any = None
    seconds: float = 0.0
    blocked: bool = False


@dataclass
class RunResult:
    transcript: Transcription | None = None
    transcript_text: str = ""          # may be human-corrected
    human_edited: bool = False
    findings: list[CriterionFinding] = field(default_factory=list)
    placement: Placement | None = None
    drills: DrillSet | None = None
    injection_hits: list = field(default_factory=list)
    quote_checks: list = field(default_factory=list)
    over_claims: list[str] = field(default_factory=list)
    trace: list[TraceStep] = field(default_factory=list)
    ledger: Ledger = field(default_factory=Ledger)

    @property
    def passed_guardrails(self) -> bool:
        return not self.over_claims and all(q.found for q in self.quote_checks)


def transcribe_step(*, image_data_url: str, res: RunResult) -> RunResult:
    """Read the image and scan it for injected instructions. No grading yet."""
    t0 = time.time()
    res.transcript = agents.transcribe(image_data_url=image_data_url, ledger=res.ledger)
    res.transcript_text = res.transcript.text
    res.trace.append(
        TraceStep(
            "transcriber",
            f"{len(res.transcript.text.split())} words, "
            f"confidence {res.transcript.confidence:.2f}"
            + (
                f", {len(res.transcript.illegible_spans)} illegible"
                if res.transcript.illegible_spans
                else ""
            ),
            res.transcript.text,
            time.time() - t0,
        )
    )

    # Scan before anything reasons over the text.
    t0 = time.time()
    res.injection_hits = guardrails.find_injection_attempts(res.transcript.text)
    res.trace.append(
        TraceStep(
            "guardrail:injection",
            (
                f"BLOCKED -- {len(res.injection_hits)} instruction-like span(s) "
                "found in the composition and treated as data"
                if res.injection_hits
                else "no instruction-like text in the composition"
            ),
            [h.excerpt for h in res.injection_hits],
            time.time() - t0,
            blocked=bool(res.injection_hits),
        )
    )
    return res


def assess_step(
    *, prompt_text: str, res: RunResult, parallel: bool = True
) -> RunResult:
    """Grade `res.transcript_text`, which may have been corrected by a human."""
    transcript = res.transcript_text

    # --- four criterion specialists ----------------------------------------
    t0 = time.time()

    def one(c: str) -> CriterionFinding:
        return agents.evaluate_criterion(
            criterion=c, transcript=transcript, prompt_text=prompt_text,
            ledger=res.ledger,
        )

    if parallel:
        # Threads, not asyncio: the client is synchronous and the work is
        # entirely network-bound.
        with ThreadPoolExecutor(max_workers=4) as pool:
            res.findings = list(pool.map(one, CRITERIA))
    else:
        res.findings = [one(c) for c in CRITERIA]

    spread = ", ".join(
        f"{f.criterion}={f.consistent_with_level[:4]} "
        f"{f.consistent_with_sublevel or ''}".strip()
        for f in res.findings
    )
    res.trace.append(
        TraceStep(
            "eval_F/A/C/T",
            spread,
            [f.model_dump() for f in res.findings],
            time.time() - t0,
        )
    )

    # --- deterministic quote check -----------------------------------------
    t0 = time.time()
    res.quote_checks = guardrails.check_quotes(transcript, res.findings)
    bad = [q for q in res.quote_checks if not q.found]
    res.trace.append(
        TraceStep(
            "guardrail:quotes",
            f"{len(res.quote_checks) - len(bad)}/{len(res.quote_checks)} quotes verified"
            + (f" -- {len(bad)} FABRICATED" if bad else ""),
            [q.quote for q in bad],
            time.time() - t0,
            blocked=bool(bad),
        )
    )

    # --- adjudicate ---------------------------------------------------------
    t0 = time.time()
    res.placement = agents.adjudicate(
        findings=res.findings, transcript=transcript, ledger=res.ledger
    )
    res.trace.append(
        TraceStep(
            "adjudicator",
            f"consistent with {res.placement.consistent_with_level} "
            f"{res.placement.consistent_with_sublevel or ''} "
            f"(limited by {res.placement.limiting_criterion})",
            res.placement.model_dump(),
            time.time() - t0,
        )
    )

    # --- over-claim check ---------------------------------------------------
    t0 = time.time()
    res.over_claims = guardrails.find_over_claims(
        res.placement.rationale,
        res.placement.caveat,
        *[f.ceiling_reason for f in res.findings],
    )
    res.trace.append(
        TraceStep(
            "guardrail:over-claim",
            f"{len(res.over_claims)} over-claiming sentence(s)"
            if res.over_claims
            else "no over-claiming; reported as evidence, not a rating",
            res.over_claims,
            time.time() - t0,
            blocked=bool(res.over_claims),
        )
    )

    # --- drills -------------------------------------------------------------
    t0 = time.time()
    res.drills = agents.generate_drills(
        placement=res.placement, findings=res.findings, ledger=res.ledger
    )
    res.trace.append(
        TraceStep(
            "drill_generator",
            f"{len(res.drills.drills)} items targeting {res.placement.limiting_criterion}",
            res.drills.model_dump(),
            time.time() - t0,
        )
    )
    return res


def run(
    *,
    image_data_url: str,
    prompt_text: str,
    parallel: bool = True,
    label: str = "run",
) -> RunResult:
    """Full pipeline, no human in the loop. Used by the CLI and the harness."""
    res = RunResult(ledger=Ledger(label=label))
    transcribe_step(image_data_url=image_data_url, res=res)
    return assess_step(prompt_text=prompt_text, res=res, parallel=parallel)
