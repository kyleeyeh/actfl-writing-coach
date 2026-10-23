"""Extract the ACTFL Writing descriptors from the official PDF into JSON.

The app grades against the published wording, not a paraphrase, so the rubric
is extracted from the source document rather than retyped. Run once:

    python scripts/build_rubric.py path/to/ACTFL-Proficiency-Guidelines-2024.pdf

Writes rubric/actfl_writing.json. The Writing domain occupies pages 24-33 of
the 2024 edition; the sublevel headings are used as section boundaries.
"""

import json
import re
import sys
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "rubric" / "actfl_writing.json"

WRITING_PAGES = range(23, 33)  # 0-indexed: pp. 24-33

LEVELS = ["Novice", "Intermediate", "Advanced"]
SUBLEVELS = ["Low", "Mid", "High"]

FACT = {
    "F": {
        "name": "Functions and tasks",
        "definition": "The types of writing activities that the individual can "
        "carry out, such as completing an information form, providing a set of "
        "written instructions, or interacting with professional colleagues in an "
        "online discussion forum.",
    },
    "A": {
        "name": "Accuracy",
        "definition": "The degree to which the individual can use linguistic "
        "features (including grammar and syntax, vocabulary, cohesive devices, "
        "sociocultural knowledge, and more) to convey written messages.",
    },
    "C": {
        "name": "Context and content",
        "definition": "The situations or circumstances in which the individual can "
        "achieve writing goals, and the topic areas that the individual is able to "
        "address in writing.",
    },
    "T": {
        "name": "Text type",
        "definition": "The length and complexity of written text that the "
        "individual can produce, ranging from words and phrases to sentences, "
        "paragraphs, and multi-paragraph discourse.",
    },
}

# The guidelines are explicit that a rating requires sustained ability across
# all level-relevant situations, including unfamiliar ones (p. 24). A single
# sample cannot establish that. This string is injected into every evaluator
# prompt so the model reports evidence, never a certified rating.
VALIDITY_CAVEAT = (
    "In order to receive a rating for writing at a given proficiency level, an "
    "individual must demonstrate sustained ability to meet each of the FACT "
    "criteria for that level in all of the communication situations that pertain "
    "to that level, including situations that the individual has not encountered "
    "previously. A single writing sample therefore cannot establish a proficiency "
    "rating. Report only the evidence this sample shows, phrased as 'consistent "
    "with', and never assert a certified level."
)


def clean(text: str) -> str:
    text = text.replace("\ufffd", "'")
    text = re.sub(r"ACTFL Proficiency Guidelines 2024.Writing", " ", text)
    text = re.sub(r"\d+ \| ACTFL PROFICIENCY GUIDELINES 2024.*", " ", text)
    text = re.sub(r"\s+", " ", text)
    # Rejoin words the PDF broke across lines. Every mid-word break in this
    # document is a genuinely hyphenated compound ("sentence- level",
    # "non- alphabetic", "next- higher"), so the hyphen is kept.
    text = re.sub(r'(\w)- (\w)', r'\1-\2', text)
    return text.strip()


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    pdf = Path(sys.argv[1])
    if not pdf.exists():
        print(f"No such file: {pdf}")
        return 1

    reader = PdfReader(str(pdf))
    blob = clean(
        " ".join((reader.pages[i].extract_text() or "") for i in WRITING_PAGES)
    )

    # Build the ordered list of headings that bound each descriptor.
    headings = []
    for lvl in LEVELS:
        headings.append((f"The {lvl} Level", lvl, None))
        for sub in SUBLEVELS:
            headings.append((f"{lvl} {sub}", lvl, sub))
    headings.append(("The Superior Level", "Superior", None))
    headings.append(("The Distinguished Level", "Distinguished", None))

    # Locate each heading, then slice between consecutive hits.
    found = []
    for text, lvl, sub in headings:
        m = re.search(re.escape(text), blob)
        if m:
            found.append((m.start(), m.end(), lvl, sub))
    found.sort()

    levels: dict = {}
    for idx, (_start, end, lvl, sub) in enumerate(found):
        stop = found[idx + 1][0] if idx + 1 < len(found) else len(blob)
        body = clean(blob[end:stop])
        body = re.sub(r"Correlations with Performance.*", "", body).strip()
        node = levels.setdefault(lvl, {"summary": "", "sublevels": {}})
        if sub is None:
            node["summary"] = body
        else:
            node["sublevels"][sub] = body

    out = {
        "source": "ACTFL Proficiency Guidelines 2024 - Writing (pp. 24-33)",
        "copyright": "(c) ACTFL, Inc., 2024",
        "fact_criteria": FACT,
        "validity_caveat": VALIDITY_CAVEAT,
        "levels": levels,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote {OUT}")
    for lvl, node in levels.items():
        subs = ", ".join(node["sublevels"]) or "-"
        print(f"  {lvl:<14} summary={len(node['summary']):>5} chars  sublevels: {subs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
