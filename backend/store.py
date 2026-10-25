"""Saving assessments so the app is usable on a stack of papers.

A teacher does not assess one composition; they assess thirty, over weeks,
and need to look back at what a student was told last time. Without
persistence the app is a demo -- close the tab and the work is gone.

Runs are stored as one JSON file each under `output/runs/`. Flat files
rather than a database on purpose: a teacher can read them, copy them,
email one to a colleague, and delete the folder to start again, none of
which is true of a SQLite file they cannot open.

The student name is supplied by the teacher and is the only personal data
here. It is stored locally in the repo folder and never leaves the machine
except in the model calls, which contain the composition anyway.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import OUTPUT_DIR

RUNS = OUTPUT_DIR / "runs"


def _safe(name: str) -> str:
    cleaned = re.sub(r"[^\w\- ]+", "", name).strip().replace(" ", "_")
    return cleaned[:40] or "sin_nombre"


def _plain(obj: Any) -> Any:
    """Make dataclasses, pydantic models and the rest JSON-serialisable."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if is_dataclass(obj) and not isinstance(obj, type):
        return {k: _plain(v) for k, v in asdict(obj).items()}
    if isinstance(obj, dict):
        return {k: _plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_plain(v) for v in obj]
    return str(obj)


def save(res, *, student: str, assignment: str, source: str = "") -> Path:
    """Persist one assessment. Returns the file written."""
    RUNS.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    path = RUNS / f"{now:%Y%m%d-%H%M%S}_{_safe(student)}.json"

    payload = {
        "saved_at": now.isoformat(timespec="seconds"),
        "student": student,
        "assignment": assignment,
        "source": source,
        "rotation_applied": getattr(res, "rotation_applied", 0),
        "human_edited": res.human_edited,
        "transcript": res.transcript_text,
        "transcription_confidence": (
            res.transcript.confidence if res.transcript else None
        ),
        "placement": _plain(res.placement),
        "findings": _plain(res.findings),
        "drills": _plain(res.drills),
        "injection_hits": [h.excerpt for h in res.injection_hits],
        "quotes_verified": sum(1 for q in res.quote_checks if q.found),
        "quotes_total": len(res.quote_checks),
        "over_claims": res.over_claims,
        "ledger": res.ledger.summary(),
        "trace": [
            {
                "agent": s.agent,
                "summary": s.summary,
                "seconds": round(s.seconds, 2),
                "blocked": s.blocked,
            }
            for s in res.trace
        ],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def history(limit: int = 60) -> list[dict]:
    """Saved assessments, newest first. Corrupt files are skipped, not fatal."""
    if not RUNS.exists():
        return []
    out = []
    for p in sorted(RUNS.glob("*.json"), reverse=True)[:limit]:
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        d["_file"] = p.name
        out.append(d)
    return out


def for_student(name: str) -> list[dict]:
    """One student's assessments, oldest first, for looking at progress."""
    runs = [r for r in history(500) if r.get("student", "").lower() == name.lower()]
    return sorted(runs, key=lambda r: r["saved_at"])


def students() -> list[str]:
    seen = {}
    for r in history(500):
        n = r.get("student") or ""
        if n:
            seen[n] = seen.get(n, 0) + 1
    return sorted(seen, key=lambda n: -seen[n])
