"""Seed a demonstration student history so the progress view has something.

Runs four calibration compositions of increasing proficiency as though they
were one student's work over four weeks. Real assessments are created -- the
model actually reads each page -- only the dates are backdated.

    python scripts/seed_demo_history.py [--student "Ana M."]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

from backend import pipeline, store  # noqa: E402
from backend.usage import Ledger  # noqa: E402

CALIB = ROOT / "data" / "calibration"
# Weakest to strongest, as a student might progress over a term.
ORDER = ["B", "E", "D", "A"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--student", default="Ana M.")
    args = ap.parse_args()

    mf = json.loads((CALIB / "manifest.json").read_text(encoding="utf-8"))
    by_id = {s["id"]: s for s in mf["samples"]}
    start = datetime.now() - timedelta(days=21)

    for i, sid in enumerate(ORDER):
        raw = (CALIB / by_id[sid]["file"]).read_bytes()
        res = pipeline.RunResult(ledger=Ledger(label=f"{args.student}-{i}"))
        pipeline.transcribe_step(raw_images=[raw], rotation=0, res=res)
        pipeline.assess_step(prompt_text=mf["prompt_es"], res=res)
        p = res.placement
        f = store.save(
            res,
            student=args.student,
            assignment=f"Preséntate (semana {i * 2 + 1})",
            source=f"calib_{sid}",
            when=start + timedelta(days=i * 7),
        )
        print(
            f"  week {i * 2 + 1}: {p.consistent_with_level} "
            f"{p.consistent_with_sublevel or ''} (limited by "
            f"{p.limiting_criterion})  -> {f.name}"
        )
    print(f"\nSeeded {len(ORDER)} assessments for {args.student}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
