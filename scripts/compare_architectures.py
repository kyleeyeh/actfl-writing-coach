"""The cost-cutting experiment.

Tokenomics asks what was done to reduce cost and whether it hurt performance.
This runs both architectures over the same transcripts and reports the saving
alongside whether the two arms still agree:

    ARM A (baseline)  four criterion specialists, one call each, in parallel
    ARM B (cheap)     one combined evaluator producing all four findings

Both then go through the same adjudicator, so the only variable is the
evaluation stage. Transcription happens once and is shared, so OCR variation
cannot contaminate the comparison.

    python scripts/compare_architectures.py
    python scripts/compare_architectures.py sample_02 sample_03
"""

from __future__ import annotations

import base64
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

from app.config import OUTPUT_DIR, SAMPLES_DIR  # noqa: E402
from backend import agents, guardrails, pipeline  # noqa: E402
from backend.usage import Ledger  # noqa: E402

DEFAULT_SAMPLES = ["sample_01", "sample_02", "sample_03", "sample_04"]


def data_url(path: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()


def arm(name: str, transcript: str, prompt_text: str, combined: bool) -> dict:
    led = Ledger(label=name)
    t0 = time.time()

    if combined:
        findings = agents.evaluate_all_criteria(
            transcript=transcript, prompt_text=prompt_text, ledger=led
        )
    else:
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=4) as pool:
            findings = list(
                pool.map(
                    lambda c: agents.evaluate_criterion(
                        criterion=c,
                        transcript=transcript,
                        prompt_text=prompt_text,
                        ledger=led,
                    ),
                    pipeline.CRITERIA,
                )
            )

    placement = agents.adjudicate(
        findings=findings, transcript=transcript, ledger=led
    )
    bad = [q for q in guardrails.check_quotes(transcript, findings) if not q.found]

    return {
        "arm": name,
        "placement": f"{placement.consistent_with_level} "
        f"{placement.consistent_with_sublevel or ''}".strip(),
        "limiting": placement.limiting_criterion,
        "per_criterion": {
            f.criterion: f"{f.consistent_with_level} {f.consistent_with_sublevel or ''}".strip()
            for f in findings
        },
        "evidence_count": sum(len(f.evidence) for f in findings),
        "fabricated_quotes": len(bad),
        "seconds": round(time.time() - t0, 1),
        "ledger": led.summary(),
    }


def main() -> int:
    ids = sys.argv[1:] or DEFAULT_SAMPLES
    mf = json.loads((SAMPLES_DIR / "manifest.json").read_text(encoding="utf-8"))
    prompt_text = mf["prompt_es"]

    rows = []
    for sid in ids:
        img = SAMPLES_DIR / f"{sid}.png"
        if not img.exists():
            print(f"skipping missing {sid}")
            continue

        # Transcribe ONCE; both arms grade the identical text.
        shared = pipeline.RunResult(ledger=Ledger(label=f"{sid}:transcribe"))
        pipeline.transcribe_step(image_data_url=data_url(img), res=shared)
        transcript = shared.transcript_text
        print(f"\n### {sid} ({len(transcript.split())} words)")

        a = arm(f"{sid}:A_fanout", transcript, prompt_text, combined=False)
        b = arm(f"{sid}:B_combined", transcript, prompt_text, combined=True)

        agree = a["placement"] == b["placement"]
        per_crit_agree = sum(
            1 for c in "FACT" if a["per_criterion"].get(c) == b["per_criterion"].get(c)
        )
        print(f"  A fan-out  : {a['placement']:<22} limited by {a['limiting']} "
              f"| {a['ledger']['prompt_tokens']:>6} in {a['ledger']['completion_tokens']:>5} out "
              f"| ${a['ledger']['cost_usd']:.4f} | {a['seconds']}s | {a['evidence_count']} quotes")
        print(f"  B combined : {b['placement']:<22} limited by {b['limiting']} "
              f"| {b['ledger']['prompt_tokens']:>6} in {b['ledger']['completion_tokens']:>5} out "
              f"| ${b['ledger']['cost_usd']:.4f} | {b['seconds']}s | {b['evidence_count']} quotes")
        saving = (
            1 - b["ledger"]["cost_usd"] / a["ledger"]["cost_usd"]
            if a["ledger"]["cost_usd"]
            else 0
        )
        print(f"  -> same placement: {agree} | criteria matching: {per_crit_agree}/4 "
              f"| cost saving: {saving:.0%}")

        rows.append({"sample": sid, "agree": agree, "criteria_agree": per_crit_agree,
                     "saving": saving, "A": a, "B": b})

    if rows:
        print("\n" + "=" * 72)
        print("SUMMARY")
        print("=" * 72)
        n = len(rows)
        tot_a = sum(r["A"]["ledger"]["cost_usd"] for r in rows)
        tot_b = sum(r["B"]["ledger"]["cost_usd"] for r in rows)
        print(f"  samples                 : {n}")
        print(f"  identical placement     : {sum(r['agree'] for r in rows)}/{n}")
        print(f"  per-criterion agreement : "
              f"{sum(r['criteria_agree'] for r in rows)}/{4 * n}")
        print(f"  cost A (fan-out)        : ${tot_a:.4f}")
        print(f"  cost B (combined)       : ${tot_b:.4f}")
        print(f"  saving                  : {1 - tot_b / tot_a:.0%}" if tot_a else "")
        print(f"  evidence quotes A vs B  : "
              f"{sum(r['A']['evidence_count'] for r in rows)} vs "
              f"{sum(r['B']['evidence_count'] for r in rows)}")

        out = OUTPUT_DIR / "architecture_comparison.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nsaved: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
