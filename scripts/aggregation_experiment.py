"""Is taking the weakest of four criteria what makes the app read low?

THE HYPOTHESIS
--------------
The adjudicator places a writer at the level of their WEAKEST FACT criterion.
That follows ACTFL, which places a writer where they sustain all four. But
the four criteria here are four separate, noisy, individually conservative
estimates, and the minimum of four noisy estimates sits below the minimum of
the underlying truth -- the more criteria, the worse it gets. So a rule that
is right in principle may be biased in practice.

WHAT THIS DOES
--------------
Runs the four criterion specialists once per sample and records all four
placements. Every aggregation rule is then compared OFFLINE against the same
recorded data -- no extra API calls per rule -- against two independent
references:

    * the teacher's blind labels, for the calibration set
    * ACTFL's published AP comparison, for the AP set

It also checks something worth knowing on its own: whether the adjudicator
actually does what it was told, i.e. whether its placement equals the minimum
of the four criteria.

    python scripts/aggregation_experiment.py
"""

from __future__ import annotations

import base64
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

from app.config import OUTPUT_DIR  # noqa: E402
from backend import agents, pipeline, scale  # noqa: E402
from backend.usage import Ledger  # noqa: E402

AP_DIR = ROOT / "data" / "ap_samples"
CALIB = ROOT / "data" / "calibration"
CACHE = OUTPUT_DIR / "criterion_placements.json"


def data_url(p: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode()


def collect() -> list[dict]:
    """One pass: transcribe, then four specialists. Cached to disk."""
    if CACHE.exists():
        print(f"using cached criterion placements from {CACHE.name}")
        return json.loads(CACHE.read_text(encoding="utf-8"))

    items: list[dict] = []

    ap = json.loads((AP_DIR / "manifest.json").read_text(encoding="utf-8"))
    for s in ap["samples"]:
        if s.get("ap_score"):
            items.append(
                {
                    "set": "ap",
                    "id": s["key"],
                    "urls": [data_url(AP_DIR / f) for f in s["files"]],
                    "prompt": s["task_prompt"],
                    "ap_score": s["ap_score"],
                }
            )

    cm = json.loads((CALIB / "manifest.json").read_text(encoding="utf-8"))
    teacher = json.loads((CALIB / "teacher_labels.json").read_text(encoding="utf-8"))
    for s in cm["samples"]:
        tl = teacher["labels"][s["id"]]
        items.append(
            {
                "set": "calibration",
                "id": s["id"],
                "urls": [data_url(CALIB / s["file"])],
                "prompt": cm["prompt_es"],
                "teacher_low": scale.rank(*_split(tl["low"])),
                "teacher_high": scale.rank(*_split(tl["high"])),
            }
        )

    rows = []
    for it in items:
        led = Ledger(label=it["id"])
        res = pipeline.RunResult(ledger=led)
        pipeline.transcribe_step(image_data_url=it["urls"], res=res)

        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=4) as pool:
            findings = list(
                pool.map(
                    lambda c: agents.evaluate_criterion(
                        criterion=c,
                        transcript=res.transcript_text,
                        prompt_text=it["prompt"],
                        ledger=led,
                    ),
                    pipeline.CRITERIA,
                )
            )

        ranks = {
            f.criterion: scale.rank(f.consistent_with_level, f.consistent_with_sublevel)
            for f in findings
        }
        row = {k: v for k, v in it.items() if k != "urls"}
        row["criteria"] = ranks
        row["words"] = len(res.transcript_text.split())
        row["cost_usd"] = round(led.cost_usd, 5)
        rows.append(row)
        print(
            f"  {it['id'][:44]:<46} "
            + " ".join(f"{c}={ranks[c]}" for c in "FACT")
            + f"   spread={max(ranks.values()) - min(ranks.values())}"
        )

    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    return rows


def _split(label: str) -> tuple[str, str | None]:
    parts = label.split()
    return parts[0], (parts[1] if len(parts) > 1 else None)


RULES = {
    "min (shipped)": lambda v: min(v),
    "median": lambda v: statistics.median(v),
    "mean": lambda v: statistics.mean(v),
    "second lowest": lambda v: sorted(v)[1],
    "max": lambda v: max(v),
}


def main() -> int:
    rows = collect()
    calib = [r for r in rows if r["set"] == "calibration"]
    ap = [r for r in rows if r["set"] == "ap"]

    print()
    print("=" * 74)
    print("HOW MUCH DO THE FOUR CRITERIA DISAGREE?")
    print("=" * 74)
    spreads = [max(r["criteria"].values()) - min(r["criteria"].values()) for r in rows]
    print(f"  mean spread across F/A/C/T : {statistics.mean(spreads):.2f} sublevels")
    print(f"  max spread                 : {max(spreads)}")
    print("  A wide spread is the diagnostic signal the app is built on, but it")
    print("  is also what makes the minimum sit far below the other three.")

    print()
    print("=" * 74)
    print("AGGREGATION RULES vs THE TEACHER'S BLIND LABELS (calibration set)")
    print("=" * 74)
    print(f"  {'rule':<16}{'mean offset':>13}{'inside range':>15}")
    best = None
    for name, fn in RULES.items():
        offs, inside = [], 0
        for r in calib:
            v = list(r["criteria"].values())
            got = fn(v)
            mid = (r["teacher_low"] + r["teacher_high"]) / 2
            offs.append(got - mid)
            if r["teacher_low"] <= got <= r["teacher_high"]:
                inside += 1
        mean_off = statistics.mean(offs)
        print(f"  {name:<16}{mean_off:>+13.2f}{inside:>10}/{len(calib)}")
        if best is None or abs(mean_off) < abs(best[1]):
            best = (name, mean_off, inside)

    print()
    print("=" * 74)
    print("AGGREGATION RULES vs ACTFL's PUBLISHED AP COMPARISON (AP set)")
    print("=" * 74)
    print(f"  {'rule':<16}{'mean offset':>13}{'inside band':>15}")
    for name, fn in RULES.items():
        offs, inside, n = [], 0, 0
        for r in ap:
            band = scale.EXPECTED_BAND.get(r["ap_score"])
            if band is None:
                continue
            got = fn(list(r["criteria"].values()))
            off = scale.calibration_offset(r["ap_score"], round(got))
            offs.append(off)
            n += 1
            if off == 0:
                inside += 1
        if offs:
            print(f"  {name:<16}{statistics.mean(offs):>+13.2f}{inside:>10}/{n}")

    print()
    print(f"  Closest to the teacher: {best[0]} ({best[1]:+.2f})")
    print()
    print("  NOTE: a rule is only worth adopting if it is defensible under")
    print("  ACTFL, not merely closer to the target. ACTFL places a writer")
    print("  where all criteria are sustained, which argues for the minimum.")
    print("  The honest reading is that the minimum is right in principle and")
    print("  biased in practice, because it compounds four conservative reads.")

    out = OUTPUT_DIR / "aggregation_experiment.json"
    out.write_text(
        json.dumps(
            {
                "mean_spread": round(statistics.mean(spreads), 3),
                "rules": {
                    name: {
                        "calibration_mean_offset": round(
                            statistics.mean(
                                [
                                    fn(list(r["criteria"].values()))
                                    - (r["teacher_low"] + r["teacher_high"]) / 2
                                    for r in calib
                                ]
                            ),
                            3,
                        )
                    }
                    for name, fn in RULES.items()
                },
                "rows": rows,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"\nsaved: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
