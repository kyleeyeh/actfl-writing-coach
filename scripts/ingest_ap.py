"""Pull expert-scored handwriting samples out of College Board AP PDFs.

The AP Spanish Language "Sample Student Responses and Scoring Commentary"
PDFs contain, for one free-response task:

  * scanned images of real handwritten student responses,
  * the official score each one received, from trained AP readers,
  * published commentary explaining why.

That gives this project an expert ground truth it could not otherwise get:
genuine handwriting, scored by people qualified to score it, with the
reasoning attached.

    python scripts/ingest_ap.py ~/Desktop/ap23-apc-spanish-language-task-1.pdf
    python scripts/ingest_ap.py ~/Desktop/*.pdf

Writes images and a manifest into data/ap_samples/. Re-running is safe; each
sample is keyed by source filename plus sample id.

A NOTE ON WHAT THE SCORES MEAN
------------------------------
AP scores are 1-5 against an AP task rubric. They are NOT ACTFL levels and
there is no published conversion, so nothing here pretends otherwise. The
scores are used as an ORDERING only -- see scripts/rank_test.py.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "ap_samples"

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

# "Sample: 1A Score: 5" and "Sample 1A Score: 5" both occur.
SCORE_RE = re.compile(r"Sample:?\s*([0-9]+[A-Z])\s*Score:?\s*(\d)", re.IGNORECASE)
# AP Spanish LITERATURE scores two dimensions separately instead of giving one
# holistic score. Only the Language dimension describes the writing itself;
# Content measures literary analysis, which this project does not assess.
SPLIT_RE = re.compile(
    r"Sample:?\s*([0-9]+[A-Z])\s*Content Score:?\s*(\d).*?Language Score:?\s*(\d)",
    re.IGNORECASE | re.DOTALL,
)
# The page label stamped on each response image page, e.g. "Q1 Sample 1A 1 of 2".
PAGE_RE = re.compile(r"Q(\d+)\s+Sample\s+([0-9]+[A-Z])\s+(\d+)\s+of\s+(\d+)", re.I)


# Some years print the task overview in the PDF; others just point at the
# Chief Reader Report. When it is absent we fall back to a description of the
# task type, and flag it, because the evaluators judge Functions and tasks
# against whatever prompt they are given -- a vague prompt makes that
# criterion unfair, and the report needs to say so rather than hide it.
GENERIC_EMAIL_TASK = (
    "Email reply (interpersonal writing, 15 minutes). Read a formal email and "
    "write a reply in a formal register. The reply must address the questions "
    "asked in the message, request additional information by asking a "
    "question, and include an appropriate greeting and closing."
)


def render_page(pdf: Path, page_index: int, dest: Path, dpi: int = 200) -> bool:
    """Rasterise one PDF page to a single PNG.

    The obvious approach -- pull the embedded images out of the page -- does
    not work on these files. Older College Board PDFs hold each scan as one
    image, but newer ones slice it into dozens of horizontal bands (one
    response arrives as 79 strips of 2220x39), and those bands are overlapping
    layers rather than a clean top-to-bottom cut. Concatenating them in
    resource order produced a page with the form's printed chrome interleaved
    through the handwriting and a block of content repeated at the bottom.

    Rendering the page the way a PDF viewer would sidesteps all of that and
    works identically on every year.
    """
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(str(pdf))
    try:
        page = doc[page_index]
        bitmap = page.render(scale=dpi / 72)
        bitmap.to_pil().convert("RGB").save(dest)
    finally:
        doc.close()
    return True


def flat(text: str) -> str:
    return re.sub(r"\s+", " ", text or "")


def task_prompt_from(blob: str) -> tuple[str, bool]:
    """(prompt, is_reconstructed). True means it was not printed in the PDF."""
    m = re.search(r"Overview\s+(.{200,2000}?)(?=Sample:?\s*[0-9]+[A-Z])", blob, re.S)
    if m:
        text = flat(m.group(1))
        if "can be found in" not in text and len(text) > 200:
            return text[:1200], False
    return GENERIC_EMAIL_TASK, True


def commentary_for(blob: str, sample_id: str) -> str:
    """The commentary paragraph for one sample, up to the next sample header."""
    m = re.search(rf"Sample:?\s*{re.escape(sample_id)}\s*Score:?\s*\d", blob, re.I)
    if not m:
        return ""
    rest = blob[m.end():]
    nxt = SCORE_RE.search(rest)
    return rest[: nxt.start()].strip() if nxt else rest.strip()


def ingest(pdf: Path) -> list[dict]:
    reader = PdfReader(str(pdf))
    pages = [flat(p.extract_text()) for p in reader.pages]
    blob = " ".join(pages)

    exam = (
        "Spanish Literature"
        if re.search(r"Spanish Literature", blob, re.I)
        else "Spanish Language"
    )

    scores = {sid.upper(): int(sc) for sid, sc in SCORE_RE.findall(blob)}
    score_kind = "holistic_1_5"
    content: dict[str, int] = {}

    if not scores:
        # Literature layout: two dimensions. Use Language as the score, since
        # it is the one about writing, and keep Content alongside it.
        for sid, c, lang in SPLIT_RE.findall(blob):
            scores[sid.upper()] = int(lang)
            content[sid.upper()] = int(c)
        if scores:
            score_kind = "language_1_3"

    task_prompt, reconstructed = task_prompt_from(blob)
    if not scores:
        print(f"  !! no scores found in {pdf.name}; skipping")
        return []

    records: list[dict] = []
    for idx, page in enumerate(reader.pages):
        m = PAGE_RE.search(pages[idx])
        if not m:
            continue
        question, sample_id, part, total = (
            m.group(1), m.group(2).upper(), int(m.group(3)), int(m.group(4)),
        )
        key = f"{pdf.stem}_{sample_id}"
        name = f"{key}_p{part}.png"
        if not render_page(pdf, idx, OUT / name):
            print(f"  !! {key} page {part}: could not render")
            continue

        rec = next((r for r in records if r["key"] == key), None)
        if rec is None:
            rec = {
                "key": key,
                "source_pdf": pdf.name,
                "question": question,
                "sample_id": sample_id,
                "ap_score": scores.get(sample_id),
                "score_kind": score_kind,
                "content_score": content.get(sample_id),
                "exam": exam,
                "pages_total": total,
                "task_prompt": task_prompt,
                "task_prompt_reconstructed": reconstructed,
                "files": [],
                "commentary": commentary_for(blob, sample_id)[:2000],
            }
            records.append(rec)
        rec["files"].append(name)

    for r in records:
        r["files"].sort()
    return records


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 2

    OUT.mkdir(parents=True, exist_ok=True)
    manifest_path = OUT / "manifest.json"
    existing = (
        json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest_path.exists()
        else {"samples": []}
    )
    by_key = {r["key"]: r for r in existing["samples"]}

    for pattern in args:
        # An absolute path cannot be globbed relative to cwd, and the shell has
        # usually expanded any wildcard before we see it anyway.
        p = Path(pattern)
        matches = (
            [p]
            if p.exists()
            else sorted(Path(p.anchor or ".").glob(
                str(p.relative_to(p.anchor)) if p.anchor else pattern
            ))
        )
        for pdf in matches:
            if not pdf.exists():
                print(f"  !! missing {pdf}")
                continue
            print(f"\n{pdf.name}")
            for rec in ingest(pdf):
                by_key[rec["key"]] = rec
                pages_note = (
                    f"{len(rec['files'])}/{rec['pages_total']} page(s)"
                    if rec["pages_total"] > 1
                    else "1 page"
                )
                extra = (
                    f" (Language; Content {rec['content_score']})"
                    if rec["score_kind"] == "language_1_3"
                    else ""
                )
                print(
                    f"  {rec['key']:<46} AP score {rec['ap_score']}{extra}  {pages_note}"
                )

    samples = sorted(by_key.values(), key=lambda r: (r["source_pdf"], r["sample_id"]))
    manifest_path.write_text(
        json.dumps({"samples": samples}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\n{len(samples)} expert-scored sample(s) in {OUT}")
    dist: dict[int, int] = {}
    for s in samples:
        dist[s["ap_score"]] = dist.get(s["ap_score"], 0) + 1
    print("  score distribution: " + ", ".join(f"{k}:{v}" for k, v in sorted(dist.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
