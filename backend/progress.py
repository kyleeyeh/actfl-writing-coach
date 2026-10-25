"""One student, across submissions: did the gap we named actually close?

WHY THIS IS THE POINT OF THE PROJECT
------------------------------------
Everything else here assesses a composition in isolation, which is exactly
what ACTFL says cannot establish a proficiency rating (Guidelines 2024,
p. 24: sustained performance across many situations). A single sample can
only ever be evidence.

Several samples over time are a different thing. The app names one limiting
criterion per submission and generates practice for it; the question a
teacher actually wants answered is whether that practice worked. This module
answers it by comparing consecutive assessments of the same student.

WHY A MISCALIBRATED APP CAN STILL MEASURE CHANGE
------------------------------------------------
The app reads about 1.5 sublevels low. That is fatal for reporting a level
and much less damaging for reporting a change, because a bias that is
roughly constant cancels when you subtract two measurements taken the same
way.

"Roughly" is carrying weight there, and this is not yet validated: the
measured bias widens at higher proficiency, so it does not cancel exactly,
and a student improving across that range would have their gain understated.
Deltas here are reported as the app's own movement, not as certified
progress, and the UI says so.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from backend import scale, store

CRITERIA = ("F", "A", "C", "T")


@dataclass
class Point:
    """One submission in a student's history."""

    saved_at: str
    assignment: str
    overall: str
    overall_rank: int
    limiting: str
    criteria: dict = field(default_factory=dict)       # letter -> label
    criterion_ranks: dict = field(default_factory=dict)  # letter -> int
    words: int = 0


@dataclass
class Movement:
    """What changed between two consecutive submissions."""

    criterion: str
    was_limiting: bool
    delta: int
    before: str
    after: str

    @property
    def closed(self) -> bool:
        return self.was_limiting and self.delta > 0


def _label(level: str | None, sub: str | None) -> str:
    return scale.label(level, sub) if level else "?"


def timeline(student: str) -> list[Point]:
    """A student's assessments, oldest first."""
    out: list[Point] = []
    for r in store.for_student(student):
        p = r.get("placement") or {}
        level, sub = p.get("consistent_with_level"), p.get("consistent_with_sublevel")
        if not level:
            continue
        ranks, labels = {}, {}
        for f in r.get("findings", []):
            c = f.get("criterion")
            if c in CRITERIA and f.get("consistent_with_level"):
                ranks[c] = scale.rank(
                    f["consistent_with_level"], f.get("consistent_with_sublevel")
                )
                labels[c] = _label(
                    f["consistent_with_level"], f.get("consistent_with_sublevel")
                )
        out.append(
            Point(
                saved_at=r["saved_at"],
                assignment=r.get("assignment", "")[:80],
                overall=_label(level, sub),
                overall_rank=scale.rank(level, sub),
                limiting=p.get("limiting_criterion", ""),
                criteria=labels,
                criterion_ranks=ranks,
                words=len((r.get("transcript") or "").split()),
            )
        )
    return out


def movements(points: list[Point]) -> list[list[Movement]]:
    """Per-criterion change between each consecutive pair of submissions."""
    out = []
    for prev, cur in zip(points, points[1:]):
        step = []
        for c in CRITERIA:
            if c in prev.criterion_ranks and c in cur.criterion_ranks:
                step.append(
                    Movement(
                        criterion=c,
                        was_limiting=(prev.limiting == c),
                        delta=cur.criterion_ranks[c] - prev.criterion_ranks[c],
                        before=prev.criteria.get(c, "?"),
                        after=cur.criteria.get(c, "?"),
                    )
                )
        out.append(step)
    return out


def summary(student: str) -> dict:
    """Everything the progress screen needs, in one call."""
    points = timeline(student)
    if len(points) < 2:
        return {"points": points, "enough": False}

    steps = movements(points)
    targeted = [m for step in steps for m in step if m.was_limiting]
    closed = [m for m in targeted if m.closed]

    # Did the overall placement move, and did the bottleneck shift? A
    # bottleneck that moves to a different criterion is usually good news:
    # the old one stopped being the binding constraint.
    first, last = points[0], points[-1]
    return {
        "points": points,
        "steps": steps,
        "enough": True,
        "n": len(points),
        "overall_delta": last.overall_rank - first.overall_rank,
        "first": first,
        "last": last,
        "targeted_count": len(targeted),
        "closed_count": len(closed),
        "bottleneck_moved": first.limiting != last.limiting,
        "bottlenecks": [p.limiting for p in points],
    }


def chart_rows(points: list[Point]) -> dict:
    """Per-criterion rank over time, for a line chart."""
    data: dict[str, list] = {c: [] for c in CRITERIA}
    for p in points:
        for c in CRITERIA:
            data[c].append(p.criterion_ranks.get(c))
    return data
