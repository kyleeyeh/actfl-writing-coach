"""Three-way calibration: written target vs teacher vs app.

The AP samples show whether the app ORDERS writing the way experts do. They
cannot show whether the level it prints is the right level, because AP scores
are not ACTFL levels.

This closes that gap. Six compositions, each written to target a specific
ACTFL sublevel, were labelled blind by a former Spanish teacher before any
model output existed. Running the app over them gives three independent
judgements of the same six texts:

    target   what the item was written to be
    teacher  what a human expert called it, blind
    app      what the pipeline reports

Reading the result:

    teacher agrees with target        -> the item is well made
    teacher disagrees with target     -> the ITEM is suspect, not the app;
                                         it is reported but excluded from the
                                         app's score
    app differs from teacher          -> the app is miscalibrated, and by how
                                         many sublevels in which direction

    python scripts/calibration_test.py
"""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

from app.config import OUTPUT_DIR  # noqa: E402
from backend import pipeline, scale  # noqa: E402
from backend.usage import Ledger  # noqa: E402

CALIB = ROOT / "data" / "calibration"


def parse(label: str) -> int:
    parts = label.split()
    return scale.rank(parts[0], parts[1] if len(parts) > 1 else None)


def data_url(p: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode()


def main() -> int:
    manifest = json.loads((CALIB / "manifest.json").read_text(encoding="utf-8"))
    targets = json.loads(
        (CALIB / "TARGETS_DO_NOT_READ_FIRST.json").read_text(encoding="utf-8")
    )
    tpath = CALIB / "teacher_labels.json"
    if not tpath.exists():
        print("No teacher labels yet. Expected data/calibration/teacher_labels.json")
        return 1
    teacher = json.loads(tpath.read_text(encoding="utf-8"))

    rows = []
    for s in manifest["samples"]:
        sid = s["id"]
        res = pipeline.RunResult(ledger=Ledger(label=f"calib_{sid}"))
        pipeline.transcribe_step(
            image_data_url=data_url(CALIB / s["file"]), res=res
        )
        pipeline.assess_step(prompt_text=manifest["prompt_es"], res=res)
        p = res.placement

        tl = teacher["labels"][sid]
        t_low, t_high = parse(tl["low"]), parse(tl["high"])
        t_mid = (t_low + t_high) / 2
        tgt = parse(targets[sid])
        app_rank = scale.rank(p.consistent_with_level, p.consistent_with_sublevel)

        rows.append(
            {
                "id": sid,
                "target": targets[sid],
                "target_rank": tgt,
                "teacher": (
                    tl["low"] if tl["low"] == tl["high"] else f"{tl['low']}..{tl['high']}"
                ),
                "teacher_low": t_low,
                "teacher_high": t_high,
                "teacher_mid": t_mid,
                "app": scale.label(p.consistent_with_level, p.consistent_with_sublevel),
                "app_rank": app_rank,
                "app_in_teacher_range": t_low <= app_rank <= t_high,
                "target_in_teacher_range": t_low <= tgt <= t_high,
                "app_minus_teacher": app_rank - t_mid,
                "target_minus_teacher": tgt - t_mid,
                "limiting": p.limiting_criterion,
                "words": len(res.transcript_text.split()),
                "cost_usd": round(res.ledger.cost_usd, 5),
            }
        )
        print(
            f"  {sid}  target {targets[sid]:<18} teacher {rows[-1]['teacher']:<34} "
            f"app {rows[-1]['app']}"
        )

    print()
    print("=" * 78)
    print("THREE-WAY CALIBRATION")
    print("=" * 78)
    print(f"{'':3}{'written target':<19}{'teacher (blind)':<34}{'app':<18}{'app-teacher':>12}")
    for r in rows:
        print(
            f"{r['id']:<3}{r['target']:<19}{r['teacher']:<34}{r['app']:<18}"
            f"{r['app_minus_teacher']:>+12.1f}"
        )

    good = [r for r in rows if r["target_in_teacher_range"]]
    bad = [r for r in rows if not r["target_in_teacher_range"]]

    print()
    print("-- item quality (does the teacher agree with what each item was written to be?)")
    print(f"   well-formed items : {len(good)}/{len(rows)}  {[r['id'] for r in good]}")
    if bad:
        print(f"   suspect items     : {len(bad)}/{len(rows)}  {[r['id'] for r in bad]}")
        for r in bad:
            print(
                f"     {r['id']}: written as {r['target']}, teacher said "
                f"{r['teacher']} ({r['target_minus_teacher']:+.1f} sublevels)"
            )
        print("   Suspect items are excluded from the app's score below.")

    scored = good or rows
    inside = sum(1 for r in scored if r["app_in_teacher_range"])
    mean = sum(r["app_minus_teacher"] for r in scored) / len(scored)

    print()
    print("-- app vs teacher (well-formed items only)")
    print(f"   inside the teacher's range : {inside}/{len(scored)}")
    print(f"   mean offset                : {mean:+.2f} sublevels")
    print(f"   worst single item          : "
          f"{max(scored, key=lambda r: abs(r['app_minus_teacher']))['id']} "
          f"({max(abs(r['app_minus_teacher']) for r in scored):.1f})")

    tau_app, c1, d1, t1 = scale.kendall_tau_b(
        [r["teacher_mid"] for r in rows], [r["app_rank"] for r in rows]
    )
    tau_tgt, c2, d2, t2 = scale.kendall_tau_b(
        [r["teacher_mid"] for r in rows], [r["target_rank"] for r in rows]
    )
    print()
    print("-- ordering (all six items)")
    print(f"   teacher vs app    : tau-b {tau_app:+.3f}  "
          f"(concordant {c1}, discordant {d1}, tied {t1})")
    print(f"   teacher vs target : tau-b {tau_tgt:+.3f}  "
          f"(concordant {c2}, discordant {d2}, tied {t2})")
    print()
    print("   The second line is a control: it measures the item WRITER against")
    print("   the teacher. If both lines are offset in the same direction, the")
    print("   bias is in how the descriptors get read, not in the pipeline.")

    out = OUTPUT_DIR / "calibration_result.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "n": len(rows),
                "well_formed": [r["id"] for r in good],
                "suspect": [r["id"] for r in bad],
                "app_inside_teacher_range": inside,
                "app_mean_offset": round(mean, 3),
                "tau_teacher_vs_app": round(tau_app, 4),
                "tau_teacher_vs_target": round(tau_tgt, 4),
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
