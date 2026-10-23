"""Turning an ACTFL placement into a number, for comparison only.

ACTFL levels are ordinal, not numeric: Intermediate Mid is above Intermediate
Low, but it is not "5 out of 11" of anything, and the gaps between rungs are
not equal. The index below exists solely so two placements can be ordered.
Do not average these numbers or report them as scores.
"""

from __future__ import annotations

ORDER = [
    ("Novice", "Low"),
    ("Novice", "Mid"),
    ("Novice", "High"),
    ("Intermediate", "Low"),
    ("Intermediate", "Mid"),
    ("Intermediate", "High"),
    ("Advanced", "Low"),
    ("Advanced", "Mid"),
    ("Advanced", "High"),
    ("Superior", None),
    ("Distinguished", None),
]

INDEX = {pair: i for i, pair in enumerate(ORDER)}


def rank(level: str, sublevel: str | None) -> int:
    """Ordinal position of a placement. Unknown sublevel falls to the level's base."""
    if (level, sublevel) in INDEX:
        return INDEX[(level, sublevel)]
    for (lvl, sub), i in INDEX.items():
        if lvl == level:
            return i
    raise ValueError(f"Unknown level: {level!r}")


def label(level: str, sublevel: str | None) -> str:
    return f"{level} {sublevel}".strip() if sublevel else level


# What ACTFL itself says an AP score corresponds to, as a band of sublevels.
#
# Source: ACTFL, "Seal of Biliteracy -- Comparison of Scales" talking points:
#   "Anecdotal evidence and examination of the scoring rubric indicate that
#    students who are showing evidence of Intermediate Mid proficiency are
#    likely to score a 3 (passing score) on the AP Language and Culture Exam;
#    students showing evidence of Intermediate High proficiency are likely to
#    score a 4 or 5; students showing evidence of Advanced level proficiency
#    are the most likely to score a 5."
#
# THREE CAVEATS, ALL OF WHICH MATTER
# ----------------------------------
# 1. ACTFL calls this anecdotal and rubric-based, not a validation study.
# 2. The statement runs proficiency -> AP score. Reading it backwards, as a
#    band of expected proficiency per score, is an inversion ACTFL did not
#    make, and it is only loosely defensible.
# 3. It concerns the WHOLE AP exam across all four skills. Our samples are a
#    single 15-minute writing task. A narrower sample should be expected to
#    show less, so some conservatism here is correct rather than an error.
#
# Used only to report a calibration offset, never to assign a level.
EXPECTED_BAND: dict[int, tuple[int, int] | None] = {
    1: None,  # not addressed by the ACTFL statement
    2: None,  # not addressed
    3: (INDEX[("Intermediate", "Mid")], INDEX[("Intermediate", "Mid")]),
    4: (INDEX[("Intermediate", "High")], INDEX[("Intermediate", "High")]),
    5: (INDEX[("Intermediate", "High")], INDEX[("Advanced", "Mid")]),
}


def calibration_offset(ap_score: int, actfl_rank: int) -> int | None:
    """Sublevels above (+) or below (-) the band ACTFL associates with a score.

    0 means inside the band. None means ACTFL says nothing about that score.
    """
    band = EXPECTED_BAND.get(ap_score)
    if band is None:
        return None
    low, high = band
    if actfl_rank < low:
        return actfl_rank - low
    if actfl_rank > high:
        return actfl_rank - high
    return 0


def kendall_tau_b(xs: list[float], ys: list[float]) -> tuple[float, int, int, int]:
    """Kendall's tau-b, plus concordant/discordant/tied pair counts.

    Written out rather than pulled from scipy: it is a dozen lines, it keeps
    the dependency list short enough that a grader's fresh clone installs
    quickly, and with a handful of samples the tie correction matters.
    """
    n = len(xs)
    con = dis = tie_x = tie_y = 0
    for i in range(n):
        for j in range(i + 1, n):
            dx, dy = xs[i] - xs[j], ys[i] - ys[j]
            if dx == 0 and dy == 0:
                tie_x += 1
                tie_y += 1
            elif dx == 0:
                tie_x += 1
            elif dy == 0:
                tie_y += 1
            elif (dx > 0) == (dy > 0):
                con += 1
            else:
                dis += 1

    denom = ((con + dis + tie_x) * (con + dis + tie_y)) ** 0.5
    tau = (con - dis) / denom if denom else 0.0
    return tau, con, dis, tie_x + tie_y
