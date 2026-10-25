"""Get a photographed page into a shape the model can actually read.

Three things go wrong with a phone photo of a sheet of paper, and all three
were hit on the first real handwritten samples:

1. **EXIF orientation.** Phones record rotation in metadata rather than
   rotating the pixels.

2. **The paper is sideways even when the photo is not.** A landscape sheet
   photographed by a phone held upright has correct EXIF and vertical text.
   EXIF cannot help; the page itself must be examined. This produced a
   transcript of `[ilegible]` at confidence 0.02.

3. **Size.** A 4000px photo costs vision tokens without being any more
   legible than 1600px.

WHAT THIS MODULE DECIDES, AND WHAT IT REFUSES TO
------------------------------------------------
It decides the AXIS: whether the lines of writing run across the image or
down it. The ink projection profile does this reliably -- on a real sideways
page the two axes scored 2.97 against 0.35 -- because lines of writing make
ink density vary strongly along the axis perpendicular to them.

It does NOT decide which way up. That is invisible to the profile (a page
and the same page upside-down have identical row profiles), and two other
approaches were tried and rejected on measured evidence:

* **Ask the model, trust its confidence.** Catastrophic. On a real control
  sheet the model returned a completely fabricated composition at
  confidence 0.98 for the upside-down rendering, while the correct
  orientation scored 0.83. Two of four rotations produced fluent invented
  text with high confidence. Confidence is anti-correlated with truth here.

* **Transcribe twice and look for instability.** Hallucinations were
  perfectly stable: similarity 1.00 across repeated calls. Decoding is
  deterministic enough that repetition reveals nothing.

* **Ascender/descender asymmetry.** Latin text carries more ink above the
  line centre than below, so flipping should invert the measure. On real
  handwriting the signal was swamped by noise and ranked the correct
  rotation third on one sample.

So the flip is left to the person looking at the page, who resolves it
instantly. `suggest_rotations()` returns the two candidates on the correct
axis, best guess first, and the interface offers a rotate control.
"""

from __future__ import annotations

import base64
import io
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageOps

MAX_WIDTH = 1600
PROFILE_WIDTH = 500


@dataclass
class Candidate:
    image: Image.Image
    rotation: int
    score: float

    def data_url(self) -> str:
        buf = io.BytesIO()
        self.image.save(buf, format="PNG")
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def load(raw: bytes | Image.Image) -> Image.Image:
    """EXIF-correct and downscale. No rotation guessing."""
    img = Image.open(io.BytesIO(raw)) if isinstance(raw, bytes) else raw
    img = ImageOps.exif_transpose(img).convert("RGB")
    if img.width > MAX_WIDTH:
        img = img.resize(
            (MAX_WIDTH, int(img.height * MAX_WIDTH / img.width)), Image.LANCZOS
        )
    return img


def _line_score(img: Image.Image) -> float:
    """Plausibility that this orientation has horizontal lines of text.

    A ranking signal only -- see the module docstring for why it is not
    trusted as a decision.
    """
    g = img.convert("L")
    g = g.resize((PROFILE_WIDTH, max(1, int(g.height * PROFILE_WIDTH / g.width))))
    a = np.asarray(g, dtype=np.float32)
    paper = float(np.percentile(a, 85)) or 255.0
    mask = a < paper * 0.72
    if not mask.any():
        return 0.0

    # Restrict to the inked region; blank paper otherwise dominates.
    rows_any, cols_any = mask.sum(axis=1), mask.sum(axis=0)

    def span(p: np.ndarray) -> tuple[int, int]:
        hits = np.flatnonzero(p >= max(1.0, p.max() * 0.08))
        return (int(hits[0]), int(hits[-1]) + 1) if hits.size else (0, p.size)

    y0, y1 = span(rows_any)
    x0, x1 = span(cols_any)
    crop = mask[y0:y1, x0:x1] if (y1 - y0 >= 8 and x1 - x0 >= 8) else mask

    rows = crop.sum(axis=1).astype(np.float64)
    mean = rows.mean()
    return float(rows.var() / (mean * mean)) if mean > 0 else 0.0


def rotate(img: Image.Image, degrees: int) -> Image.Image:
    d = degrees % 360
    return img if d == 0 else img.rotate(-d, expand=True, fillcolor=(255, 255, 255))


def suggest_rotations(raw: bytes | Image.Image) -> tuple[list[int], dict]:
    """(candidate rotations on the correct axis, per-rotation scores).

    The first element is the better guess, but only the axis is trustworthy
    -- see the module docstring. Callers should let a human confirm.
    """
    base = load(raw)
    scores = {r: round(_line_score(rotate(base, r)), 3) for r in (0, 90, 180, 270)}
    horizontal = max(scores[0], scores[180])
    vertical = max(scores[90], scores[270])
    pair = (0, 180) if horizontal >= vertical else (270, 90)
    return list(pair), scores


def axis_is_clear(scores: dict) -> bool:
    """Whether the profile separated the two axes convincingly."""
    horizontal = max(scores[0], scores[180])
    vertical = max(scores[90], scores[270])
    lo = min(horizontal, vertical)
    return lo <= 0 or max(horizontal, vertical) / lo >= 2.0
