"""Can the transcriber be made to say "I can't read this" instead of inventing?

THE FAILURE
-----------
Shown an upside-down or sideways page, the model does not refuse. It returns
a fluent, plausible, entirely invented Spanish composition and reports high
confidence. On one real control sheet, two of four rotations produced
fabricated text at confidence 0.98, while the correct orientation scored
0.83.

THE QUESTION
------------
Is that a property of the model, or of how it was asked? The original prompt
says "transcribe this" and never gives it permission to fail. This compares
prompt variants on the same four rotations of a page whose true text is
known, and scores each on two things:

    correct rotation  -> should transcribe accurately (high similarity)
    wrong rotations   -> should ABSTAIN, not invent

A variant only wins if it does both. A prompt that abstains on everything is
useless, so accuracy on the correct rotation is checked too.

    python scripts/abstention_experiment.py
"""

from __future__ import annotations

import difflib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

from app.config import OUTPUT_DIR  # noqa: E402
from backend import imaging  # noqa: E402
from backend.client import ContentFiltered, call_json  # noqa: E402
from backend.schemas import Transcription  # noqa: E402
from backend.usage import Ledger  # noqa: E402

PAGE = ROOT / "data" / "samples" / "hw_control.png"
CORRECT_ROTATION = 270
TRUE_TEXT = (
    "Hola, me llamo Javier y tengo dieciseis años. Vivo en Chicago con mi "
    "familia. Mi hermano se llama Luis y el es muy comico. Me gusta jugar "
    "futbol pero no me gusta la tarea."
)

BASE = (
    "Transcribe the handwritten Spanish composition in this image.\n\n"
    "This is a DIPLOMATIC transcription. Reproduce exactly what is on the "
    "page, including spelling mistakes, missing or wrong accents, incorrect "
    "verb forms, and crossed-out words (render a crossing-out as [tachado: "
    "word]). Do not correct, improve, or standardise anything. The errors "
    "are the data being assessed -- silently fixing one destroys the "
    "evidence.\n\n"
    "If any word is unreadable, write [ilegible] and list it."
)

ABSTAIN = (
    "\n\n=== BEFORE YOU TRANSCRIBE ===\n"
    "First decide whether you can actually read this page. The image may be "
    "upside-down, sideways, blank, blurred, or not a composition at all.\n\n"
    "If you cannot read the writing as Spanish prose running left to right, "
    "you MUST return exactly \"[ilegible]\" as the text, confidence 0.0, and "
    "stop. Do not reconstruct what a page like this probably says. Do not "
    "produce a composition that would be plausible for this assignment. An "
    "invented transcript is worse than no transcript, because it will be "
    "graded as a real student's work and they will be given feedback on "
    "sentences they never wrote.\n\n"
    "Returning \"[ilegible]\" when the page is unreadable is the correct and "
    "expected answer, not a failure.\n\n"
    "`confidence` must describe how certain you are that these are the words "
    "ON THE PAGE -- not how fluent your output is. If you are reconstructing "
    "rather than reading, confidence is below 0.2."
)

ORIENT = (
    "\n\n=== ORIENTATION CHECK ===\n"
    "Before transcribing, check the page orientation. Say what you see: if "
    "the lines of writing do not run horizontally left-to-right, the page is "
    "rotated and you cannot read it. Return \"[ilegible]\" with confidence "
    "0.0 rather than attempting it."
)

VARIANTS = {
    "baseline": BASE,
    "abstain": BASE + ABSTAIN,
    "abstain+orient": BASE + ABSTAIN + ORIENT,
}


def looks_abstained(text: str) -> bool:
    t = text.strip().lower()
    return len(t) < 40 and ("ilegible" in t or "illegible" in t or not t)


def main() -> int:
    raw = PAGE.read_bytes()
    base = imaging.load(raw)
    led = Ledger(label="abstention")
    results: dict[str, dict] = {}

    for name, prompt in VARIANTS.items():
        print(f"\n### {name}")
        rows = {}
        for rot in (0, 90, 180, 270):
            url = imaging.Candidate(
                image=imaging.rotate(base, rot), rotation=rot, score=0.0
            ).data_url()
            try:
                t = call_json(
                    agent=f"transcribe[{name}]",
                    task=prompt,
                    out_model=Transcription,
                    ledger=led,
                    user_content=[{"type": "image_url", "image_url": {"url": url}}],
                )
                text, conf = t.text.strip(), t.confidence
            except ContentFiltered:
                text, conf = "[content filtered]", 0.0

            sim = difflib.SequenceMatcher(None, TRUE_TEXT.lower(), text.lower()).ratio()
            abstained = looks_abstained(text)
            correct = rot == CORRECT_ROTATION
            verdict = (
                ("READ OK" if sim > 0.6 else "MISREAD")
                if correct
                else ("abstained" if abstained else "INVENTED")
            )
            rows[rot] = {
                "confidence": round(conf, 2),
                "similarity_to_truth": round(sim, 2),
                "abstained": abstained,
                "verdict": verdict,
                "text": text[:110],
            }
            flag = "<-- correct rotation" if correct else ""
            print(
                f"  rot {rot:>3}  conf {conf:.2f}  sim {sim:.2f}  "
                f"{verdict:<10} {flag}"
            )
            if not correct and not abstained:
                print(f"            invented: {text[:88]!r}")

        wrong = [r for rot, r in rows.items() if rot != CORRECT_ROTATION]
        results[name] = {
            "rows": rows,
            "abstained_on_wrong": sum(1 for r in wrong if r["abstained"]),
            "wrong_total": len(wrong),
            "correct_similarity": rows[CORRECT_ROTATION]["similarity_to_truth"],
        }
        r = results[name]
        print(
            f"  => abstained on {r['abstained_on_wrong']}/{r['wrong_total']} "
            f"unreadable rotations; similarity on the correct one "
            f"{r['correct_similarity']:.2f}"
        )

    out = OUTPUT_DIR / "abstention_experiment.json"
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nsaved: {out}")
    print(f"total cost: ${led.cost_usd:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
