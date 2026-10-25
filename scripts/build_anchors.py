"""Build the calibration anchors injected into every evaluator prompt.

WHY
---
The app reads about 1.5 ACTFL sublevels low. Roughly 1.2 of that came from
taking the weakest of four criteria; the rest sits inside each individual
criterion judgement. Asked to justify a level purely from descriptor prose,
the model finds reasons the sample is not yet at the next rung and settles
low. That is what contrastive anchors are the standard remedy for: show the
grader what each rung actually looks like.

WHERE THE LABELS COME FROM
--------------------------
A former Spanish teacher read six compositions blind -- before seeing any
output from this app, and without access to the levels they were written to
target -- and assigned a level to each. Those judgements are the anchors.
They are one expert's opinion, not a certified rating, and the report says
so.

WHY THIS IS NOT CIRCULAR
------------------------
The anchors come from the six-item calibration set. That set can therefore
no longer be used to measure whether the anchors worked. The measurement is
made on the 18 College Board AP samples, which are scored by different
people, on a different instrument, and are not used here at all.

    python scripts/build_anchors.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

CALIB = ROOT / "data" / "calibration"
DEST = ROOT / "rubric" / "anchors.json"

# The compositions live in the generator; importing it keeps one copy.
sys.path.insert(0, str(ROOT / "scripts"))
from make_calibration_set import ITEMS  # noqa: E402

MAX_CHARS = 420


def excerpt(text: str) -> str:
    if len(text) <= MAX_CHARS:
        return text
    cut = text[:MAX_CHARS]
    return cut[: cut.rfind(" ")] + " […]"


def main() -> int:
    labels = json.loads(
        (CALIB / "teacher_labels.json").read_text(encoding="utf-8")
    )["labels"]

    anchors = []
    for it in ITEMS:
        lab = labels.get(it["id"])
        if not lab:
            continue
        # Where the rater gave a range, use the lower bound: it is the level
        # the sample is claimed to SUSTAIN, which is what ACTFL placement
        # means, and it keeps the anchors from pulling the model too high.
        level = lab.get("lean") or lab["low"]
        anchors.append(
            {
                "id": it["id"],
                "level": level,
                "rater_range": (
                    lab["low"] if lab["low"] == lab["high"]
                    else f"{lab['low']}–{lab['high']}"
                ),
                "words": len(it["text"].split()),
                "text": excerpt(it["text"]),
            }
        )

    anchors.sort(key=lambda a: a["words"])
    DEST.write_text(
        json.dumps(
            {
                "source": (
                    "Blind judgements by a former high-school Spanish teacher, "
                    "made before any output from this app existed."
                ),
                "caveat": (
                    "One expert's opinion on six short compositions, not a "
                    "certified ACTFL rating. Used to calibrate, not to verify."
                ),
                "anchors": anchors,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"wrote {DEST}")
    for a in anchors:
        print(f"  {a['id']}  {a['level']:<20} ({a['words']} words)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
