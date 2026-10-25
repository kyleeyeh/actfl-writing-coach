"""Run the full pipeline against one sample image, from the command line.

    python scripts/run_sample.py sample_02
    python scripts/run_sample.py sample_05_injection --serial

Prints the run trace and the token ledger, and writes both to output/ so the
numbers can be quoted in the report without being retyped.
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

from app.config import OUTPUT_DIR, PRICING_IS_PLACEHOLDER, SAMPLES_DIR  # noqa: E402
from backend import pipeline  # noqa: E402
from backend.pipeline import Unreadable  # noqa: E402


def _sample_prompt(manifest: dict, sample_id: str) -> str:
    """Per-sample prompt if the manifest carries one, else the shared one.

    The handwritten samples answer a self-introduction prompt rather than the
    vacation prompt the rendered fixtures use, and grading a composition
    against the wrong assignment marks down Functions and tasks for a task
    that was never set.
    """
    for s in manifest["samples"]:
        if s["id"] == sample_id and s.get("prompt"):
            return s["prompt"]
    return manifest["prompt_es"]


def data_url(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("sample", help="sample id, e.g. sample_02")
    ap.add_argument(
        "--rotate",
        type=int,
        default=None,
        help="degrees to rotate the page before reading; omit to use the "
             "detected axis (the app will tell you if it is unsure)",
    )
    ap.add_argument(
        "--serial",
        action="store_true",
        help="run the four criterion agents one at a time instead of in parallel",
    )
    args = ap.parse_args()

    manifest = json.loads((SAMPLES_DIR / "manifest.json").read_text(encoding="utf-8"))
    img = SAMPLES_DIR / f"{args.sample}.png"
    if not img.exists():
        print(f"No such sample: {img}")
        print("Available:", ", ".join(s["id"] for s in manifest["samples"]))
        return 1

    raw = img.read_bytes()
    if args.rotate is None:
        from backend import imaging

        cands, scores = imaging.suggest_rotations(raw)
        rotation = cands[0]
        if not imaging.axis_is_clear(scores):
            print(
                f"  ! page orientation is unclear (scores {scores}). Using "
                f"{rotation} degrees; pass --rotate if the transcript looks wrong."
            )
    else:
        rotation = args.rotate

    print(f"Running {args.sample} at rotation {rotation} degrees ...\n")
    try:
        res = pipeline.run(
            raw_images=[raw],
            rotation=rotation,
            prompt_text=_sample_prompt(manifest, args.sample),
            parallel=not args.serial,
            label=args.sample,
        )
    except Unreadable as exc:
        print(f"  UNREADABLE: {exc}")
        return 2

    print("=" * 72)
    print("RUN TRACE")
    print("=" * 72)
    for i, step in enumerate(res.trace, 1):
        mark = "!!" if step.blocked else "  "
        print(f"{mark} {i}. {step.agent:<22} {step.summary}  [{step.seconds:.1f}s]")

    print("\n" + "=" * 72)
    print("TRANSCRIPT (diplomatic)")
    print("=" * 72)
    print(res.transcript.text)

    if res.injection_hits:
        print("\n" + "=" * 72)
        print(f"INJECTION DETECTED -- {len(res.injection_hits)} span(s), treated as data")
        print("=" * 72)
        for h in res.injection_hits:
            print(f"  ...{h.excerpt}...")

    print("\n" + "=" * 72)
    print("PLACEMENT")
    print("=" * 72)
    p = res.placement
    print(f"  consistent with : {p.consistent_with_level} {p.consistent_with_sublevel or ''}")
    print(f"  limited by      : {p.limiting_criterion}")
    print(f"  next target     : {p.next_sublevel_target}")
    print(f"  rationale       : {p.rationale}")
    print(f"  caveat          : {p.caveat}")

    print("\n  per criterion:")
    for f in res.findings:
        print(
            f"    {f.criterion}: {f.consistent_with_level} "
            f"{f.consistent_with_sublevel or '':<5} ceiling: {f.ceiling_reason}"
        )

    print("\n" + "=" * 72)
    print("DRILLS")
    print("=" * 72)
    for d in res.drills.drills:
        print(f"  [{d.kind}] ({d.targets_criterion}) {d.title}")
        print(f"      to student (en): {d.explanation_en}")
        print(f"      task (es)      : {d.task_es}")
        print(f"      teacher (en)   : {d.teacher_note_en}")

    print("\n" + "=" * 72)
    print("GUARDRAILS")
    print("=" * 72)
    bad = [q for q in res.quote_checks if not q.found]
    print(f"  quotes verified : {len(res.quote_checks) - len(bad)}/{len(res.quote_checks)}")
    for q in bad:
        print(f"    NOT FOUND [{q.criterion}]: {q.quote!r}")
    print(f"  over-claims     : {len(res.over_claims)}")
    for o in res.over_claims:
        print(f"    {o}")
    print(f"  overall         : {'PASS' if res.passed_guardrails else 'FAIL'}")

    print("\n" + "=" * 72)
    print("TOKENS")
    print("=" * 72)
    print(res.ledger.table())
    if PRICING_IS_PLACEHOLDER:
        print("\n  NOTE: prices in app/config.py are still 0.0 placeholders;")
        print("        dollar figures are meaningless until the rate sheet is in.")

    mode = "serial" if args.serial else "parallel"
    led = res.ledger.save(f"ledger_{args.sample}_{mode}.json")
    (OUTPUT_DIR / f"run_{args.sample}_{mode}.json").write_text(
        json.dumps(
            {
                "transcript": res.transcript.model_dump(),
                "findings": [f.model_dump() for f in res.findings],
                "placement": res.placement.model_dump(),
                "drills": res.drills.model_dump(),
                "injection_hits": [h.excerpt for h in res.injection_hits],
                "over_claims": res.over_claims,
                "quotes_ok": not bad,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"\nsaved: {led.name} and run_{args.sample}_{mode}.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
