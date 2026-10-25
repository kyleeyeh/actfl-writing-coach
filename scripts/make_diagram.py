"""Draw the architecture diagram used in the report and slides.

Generated rather than drawn by hand so it cannot drift out of step with the
pipeline it describes.

    python scripts/make_diagram.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "report" / "figures" / "architecture.png"

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

W, H = 1500, 1000
INK = "#16202e"
MUTED = "#5b6b7f"
ACCENT = "#15497a"
GUARD = "#9c2b2b"
HUMAN = "#1d6b3f"
BG = "#ffffff"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    names = (
        ("segoeuib.ttf", "arialbd.ttf", "calibrib.ttf", "DejaVuSans-Bold.ttf")
        if bold
        else ("segoeui.ttf", "arial.ttf", "calibri.ttf", "DejaVuSans.ttf")
    )
    for n in names:
        try:
            return ImageFont.truetype(n, size)
        except OSError:
            continue
    raise RuntimeError("No TrueType font available.")


def box(d, xy, title, sub=None, colour=ACCENT, fill="#f4f8fc", dashed=False):
    """Draw a box, vertically centring title and subtitle as one block.

    Laying the text out from the true content height rather than from a fixed
    offset; an earlier version used a fixed offset and clipped the second line
    of every two-line subtitle.
    """
    x1, y1, x2, y2 = xy
    d.rounded_rectangle(xy, radius=10, fill=fill, outline=colour, width=3)
    f1, f2 = font(23, True), font(17)
    title_h, line_h = 29, 22
    lines = sub.split("\n") if sub else []
    total = title_h + len(lines) * line_h
    y = (y1 + y2) / 2 - total / 2
    cx = (x1 + x2) / 2

    d.text((cx - d.textlength(title, font=f1) / 2, y), title, fill=colour, font=f1)
    for i, line in enumerate(lines):
        d.text(
            (cx - d.textlength(line, font=f2) / 2, y + title_h + i * line_h),
            line,
            fill=MUTED,
            font=f2,
        )


def arrow(d, p1, p2, colour=INK, width=3):
    d.line([p1, p2], fill=colour, width=width)
    import math

    ang = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
    size = 11
    d.polygon(
        [
            p2,
            (p2[0] - size * math.cos(ang - 0.45), p2[1] - size * math.sin(ang - 0.45)),
            (p2[0] - size * math.cos(ang + 0.45), p2[1] - size * math.sin(ang + 0.45)),
        ],
        fill=colour,
    )


def main() -> int:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    d.text((40, 26), "ACTFL Writing Coach — pipeline", fill=INK, font=font(30, True))
    d.text((40, 66), "7 model calls - gpt-6-luna via Portkey - 3 deterministic "
                     "guardrails in plain Python",
           fill=MUTED, font=font(18))

    box(d, (40, 118, 290, 212), "Photograph", "handwritten page", MUTED, "#f5f6f8")
    box(d, (340, 118, 620, 212), "Transcriber", "vision; preserves\nevery error")
    box(d, (670, 118, 980, 212), "Injection scan",
        "regex over transcript\nSpanish + English", GUARD, "#fdf4f4")
    box(d, (1030, 118, 1460, 212), "HUMAN CONFIRMS TRANSCRIPT",
        "the teacher corrects misreadings\nbefore anything is graded",
        HUMAN, "#f2faf5")

    arrow(d, (290, 165), (338, 165))
    arrow(d, (620, 165), (668, 165))
    arrow(d, (980, 165), (1028, 165))

    # Fan-out
    d.text((40, 265), "Four criterion specialists, in parallel",
           fill=INK, font=font(21, True))
    d.text((40, 293), "ACTFL assesses four criteria independently. The spread "
                      "between them is the diagnosis.", fill=MUTED, font=font(17))

    labels = [
        ("Eval F", "Functions\n& tasks"),
        ("Eval A", "Accuracy"),
        ("Eval C", "Context\n& content"),
        ("Eval T", "Text type"),
    ]
    xs = [40, 400, 760, 1120]
    for (t, s), x in zip(labels, xs):
        box(d, (x, 330, x + 340, 448), t, s)
        arrow(d, (x + 170, 316), (x + 170, 328), MUTED, 2)

    d.line([(210, 316), (1290, 316)], fill=MUTED, width=2)
    arrow(d, (1245, 236), (1245, 314), MUTED, 2)

    box(d, (40, 496, 560, 596), "Quote verification",
        "every claim must quote the transcript verbatim; checked by\n"
        "string containment, not by asking a model",
        GUARD, "#fdf4f4")
    for x in xs:
        arrow(d, (x + 170, 448), (x + 170, 472), MUTED, 2)
    d.line([(210, 472), (1290, 472)], fill=MUTED, width=2)

    box(d, (620, 496, 1000, 596), "Adjudicator",
        "weakest criterion governs;\nnames the limiting one")
    arrow(d, (750, 472), (750, 494), MUTED, 2)

    box(d, (1060, 496, 1460, 596), "Over-claim scan",
        "blocks asserting a rating\none sample cannot support",
        GUARD, "#fdf4f4")
    arrow(d, (1000, 546), (1058, 546), MUTED, 2)

    box(d, (620, 652, 1000, 752), "Drill generator",
        "practice aimed at the\nlimiting criterion")
    arrow(d, (810, 596), (810, 650))

    box(d, (1060, 652, 1460, 752), "Teacher sees",
        "evidence per criterion,\nwhat blocks the next rung,\ntargeted practice",
        HUMAN, "#f2faf5")
    arrow(d, (1000, 702), (1058, 702))

    # Footnote
    d.line([(40, 800), (1460, 800)], fill="#dfe5ec", width=2)
    d.text((40, 822),
           "Measured: ordering agrees with expert raters (tau-b +0.46 over 18 "
           "AP-scored samples, 7 discordant pairs of 69).",
           fill=INK, font=font(18))
    d.text((40, 852),
           "Absolute placement reads 1.5-2.0 ACTFL sublevels low against both "
           "a teacher's blind labels and ACTFL's own AP comparison.",
           fill=GUARD, font=font(18))
    d.text((40, 892),
           "Red = deterministic guardrail, no model involved.   "
           "Green = human in the loop.",
           fill=MUTED, font=font(17))
    d.text((40, 922),
           "Cost: $0.021 per composition, 73% of input tokens served from "
           "prompt cache.",
           fill=MUTED, font=font(17))

    DEST.parent.mkdir(parents=True, exist_ok=True)
    img.save(DEST)
    print(f"wrote {DEST}  ({img.width}x{img.height})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
