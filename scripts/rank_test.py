"""Does the app rank expert-scored samples the way the experts did?

THE VALIDATION PROBLEM, AND WHY THIS IS THE HONEST ANSWER TO IT
---------------------------------------------------------------
The app reports ACTFL evidence. The College Board samples carry AP scores on
an AP rubric. There is no published conversion between the two, and inventing
one would make every number downstream meaningless.

So this does not check whether the app reproduces AP scores. It checks
something weaker that is actually true: whether the app puts the samples in
the SAME ORDER the expert readers did. If it ranks a 5 above a 3 above a 1,
it is tracking real differences in writing quality, whatever labels it uses.

Reported as Kendall's tau-b, with the concordant and discordant pair counts,
because with a handful of samples the raw pair counts are more honest than a
single coefficient.

Results are grouped by scoring instrument and never pooled across them:

  * AP Spanish LANGUAGE -- one holistic 1-5 score for an email reply.
  * AP Spanish LITERATURE -- a separate 1-3 Language score for a literary
    analysis. Only the Language dimension is used; Content measures literary
    analysis, which this project does not claim to assess.

Two different rubrics over two different task types do not belong in one
coefficient.

    python scripts/rank_test.py
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

AP_DIR = ROOT / "data" / "ap_samples"

FALLBACK_PROMPT = (
    "Respond in writing in Spanish to the task set by the exam question, in "
    "an appropriate register and format."
)


def data_url(path: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()


def main() -> int:
    mpath = AP_DIR / "manifest.json"
    if not mpath.exists():
        print("No AP samples. Run: python scripts/ingest_ap.py <pdf>")
        return 1

    samples = [
        s
        for s in json.loads(mpath.read_text(encoding="utf-8"))["samples"]
        if s.get("ap_score")
    ]
    if len(samples) < 2:
        print("Need at least two scored samples to test an ordering.")
        return 1

    rows = []
    for s in samples:
        urls = [data_url(AP_DIR / f) for f in s["files"]]
        res = pipeline.RunResult(ledger=Ledger(label=s["key"]))
        pipeline.transcribe_step(image_data_url=urls, res=res)
        pipeline.assess_step(
            prompt_text=s.get("task_prompt") or FALLBACK_PROMPT, res=res
        )

        p = res.placement
        bad = [q for q in res.quote_checks if not q.found]
        rows.append(
            {
                "key": s["key"],
                "exam": s.get("exam", "Spanish Language"),
                "score_kind": s.get("score_kind", "holistic_1_5"),
                "ap_score": s["ap_score"],
                "content_score": s.get("content_score"),
                "actfl": scale.label(
                    p.consistent_with_level, p.consistent_with_sublevel
                ),
                "actfl_rank": scale.rank(
                    p.consistent_with_level, p.consistent_with_sublevel
                ),
                "limiting": p.limiting_criterion,
                "words": len(res.transcript_text.split()),
                "transcription_confidence": res.transcript.confidence,
                "fabricated_quotes": len(bad),
                "over_claims": len(res.over_claims),
                "injection_hits": len(res.injection_hits),
                "cost_usd": round(res.ledger.cost_usd, 5),
                "tokens": res.ledger.prompt_tokens + res.ledger.completion_tokens,
                "cache_hit_rate": round(res.ledger.cache_hit_rate, 3),
                "prompt_reconstructed": bool(s.get("task_prompt_reconstructed")),
            }
        )
        print(
            f"  {s['key']:<44} AP {s['ap_score']}  ->  {rows[-1]['actfl']:<18} "
            f"({rows[-1]['words']} words, limited by {p.limiting_criterion})"
        )

    groups: dict[str, list] = {}
    for r in rows:
        groups.setdefault(f"{r['exam']} [{r['score_kind']}]", []).append(r)

    print()
    print("=" * 72)
    print("RANK AGREEMENT WITH EXPERT AP SCORES")
    print("=" * 72)

    summary = {}
    for name, grp in sorted(groups.items()):
        tau, con, dis, ties = scale.kendall_tau_b(
            [r["ap_score"] for r in grp], [r["actfl_rank"] for r in grp]
        )
        summary[name] = {
            "n": len(grp),
            "tau_b": round(tau, 4),
            "concordant": con,
            "discordant": dis,
            "tied": ties,
        }
        print()
        print(f"-- {name}  (n={len(grp)})")
        print(f"   {'sample':<44}{'AP':>4}  ACTFL placement")
        for r in sorted(grp, key=lambda r: r["ap_score"], reverse=True):
            print(f"   {r['key']:<44}{r['ap_score']:>4}  {r['actfl']}")
        print(
            f"   concordant {con}  discordant {dis}  tied {ties}"
            f"   Kendall tau-b = {tau:+.3f}"
        )

    print()
    print("  (+1 = same order as the AP readers, 0 = none, -1 = reversed)")

    # --- absolute calibration ------------------------------------------
    # Ranking says the app orders samples correctly. It says nothing about
    # whether the level it prints is right. This compares each placement
    # against the band ACTFL associates with that AP score -- see the
    # caveats in backend/scale.py, which are substantial.
    offsets = [
        (r, scale.calibration_offset(r["ap_score"], r["actfl_rank"]))
        for r in rows
        if r["score_kind"] == "holistic_1_5"
    ]
    scored = [(r, o) for r, o in offsets if o is not None]
    if scored:
        print()
        print("=" * 72)
        print("ABSOLUTE CALIBRATION vs ACTFL's published AP comparison")
        print("=" * 72)
        inside = sum(1 for _r, o in scored if o == 0)
        mean = sum(o for _r, o in scored) / len(scored)
        print(f"  samples ACTFL's statement covers : {len(scored)} of {len(rows)}")
        print(f"  placements inside expected band  : {inside}/{len(scored)}")
        print(f"  mean offset (sublevels)          : {mean:+.2f}")
        for ap in sorted({r["ap_score"] for r, _o in scored}):
            grp = [o for r, o in scored if r["ap_score"] == ap]
            band = scale.EXPECTED_BAND[ap]
            names = (
                scale.label(*scale.ORDER[band[0]])
                if band[0] == band[1]
                else f"{scale.label(*scale.ORDER[band[0]])}..{scale.label(*scale.ORDER[band[1]])}"
            )
            print(
                f"    AP {ap} (expects {names}): "
                f"mean offset {sum(grp) / len(grp):+.2f} over n={len(grp)}"
            )
        print()
        print("  Negative = the app places lower than ACTFL's comparison implies.")
        print("  ACTFL calls that comparison anecdotal, and it describes the whole")
        print("  exam rather than one 15-minute writing task, so some conservatism")
        print("  is expected. See backend/scale.py.")

    fab = sum(r["fabricated_quotes"] for r in rows)
    over = sum(r["over_claims"] for r in rows)
    low = [r["key"] for r in rows if r["words"] < 20]
    print()
    print(f"  fabricated quotes across all runs : {fab}")
    print(f"  over-claiming sentences           : {over}")
    print(f"  suspiciously short transcripts    : {len(low)} {low}")
    print(
        f"  total cost                        : "
        f"${sum(r['cost_usd'] for r in rows):.4f}"
    )

    out = OUTPUT_DIR / "rank_test.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {"by_instrument": summary, "n": len(rows), "rows": rows},
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"\nsaved: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
