"""Download the College Board AP Spanish Language writing samples.

The expert-scored validation set is not committed to this repo. It is ~27 MB
of College Board scans, and they are their copyright to distribute, not ours.
This fetches them from AP Central instead, so the validation is reproducible
without redistributing anything.

    python scripts/fetch_ap.py
    python scripts/ingest_ap.py data/ap_pdfs/*.pdf
    python scripts/rank_test.py

Only Tasks 1 and 2 are fetched. Those are the writing tasks -- the email reply
(interpersonal) and the argumentative essay (presentational). Tasks 3 and 4
are speaking, which this project does not assess.

None of this is needed to RUN the app. The app ships with its own small
sample set in data/samples/. See the README.
"""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "ap_pdfs"
BASE = "https://apcentral.collegeboard.org/media/pdf"

YEARS = ("23", "24", "25")
TASKS = ("1", "2")

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    ok = failed = skipped = 0

    for year in YEARS:
        for task in TASKS:
            name = f"ap{year}-apc-spanish-language-task-{task}.pdf"
            dest = OUT / name
            if dest.exists() and dest.stat().st_size > 10_000:
                print(f"  have   {name}")
                skipped += 1
                continue
            try:
                req = urllib.request.Request(
                    f"{BASE}/{name}", headers={"User-Agent": "Mozilla/5.0"}
                )
                with urllib.request.urlopen(req, timeout=120) as r:
                    data = r.read()
                dest.write_bytes(data)
                print(f"  got    {name}  ({len(data) // 1024} KB)")
                ok += 1
            except Exception as exc:  # noqa: BLE001 -- report and carry on
                print(f"  FAILED {name}: {exc}")
                failed += 1

    print(f"\n{ok} downloaded, {skipped} already present, {failed} failed -> {OUT}")
    if failed:
        print("College Board may have moved a file. Browse the past exam "
              "questions page and drop the PDFs into data/ap_pdfs/ by hand.")
    return 1 if failed and not ok and not skipped else 0


if __name__ == "__main__":
    raise SystemExit(main())
