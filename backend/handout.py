"""The thing the student actually receives.

The app's own screen is built for the teacher: evidence, criteria, token
costs. None of that belongs on a page handed to a sixteen-year-old. This
builds a single self-contained HTML sheet the teacher can print or email,
written to the student, in a tone that says *here is your next step* rather
than *here is your rating*.

WHICH LANGUAGE
--------------
Everything explaining the work is in English; only the work itself is in
Spanish. The student is placed somewhere around Novice or Intermediate --
they cannot read a Spanish explanation of what is wrong with their Spanish,
and feedback you cannot decode is not feedback. The exercises stay in
Spanish, because writing Spanish is the point.

Three further choices:

* **No level is shown to the student.** The app reads about 1.5 sublevels
  low, so a level on a handout would be a number the measurements do not
  support. The teacher sees the placement and decides what to say about it.
* **One focus, not four.** Only the limiting criterion and its practice
  appear. A list of everything wrong with your Spanish is not actionable.
* **The student's own words are quoted back**, because feedback anchored to
  something you actually wrote lands differently from a generic rule.
"""

from __future__ import annotations

import html
from datetime import date

# Plain-English names. The student never sees "Functions and tasks" or any
# other piece of ACTFL vocabulary -- it would mean nothing to them.
FOCUS_NAMES = {
    "F": "the kinds of things you can do in writing",
    "A": "accuracy — spelling, accents and verb forms",
    "C": "the range of topics you can write about",
    "T": "how you put your writing together",
}

CSS = """
body{font:16px/1.6 Georgia,serif;color:#16202e;max-width:40em;margin:0 auto;
     padding:2.4em 1.6em}
h1{font-size:1.5em;margin:0 0 .1em}
.meta{color:#5b6b7f;font-size:.9em;margin-bottom:1.8em}
h2{font-size:1.1em;margin:1.8em 0 .4em;color:#15497a}
.focus{background:#f4f8fc;border-left:4px solid #15497a;padding:.9em 1.1em;
       border-radius:0 6px 6px 0}
.quote{border-left:3px solid #c3ccd8;padding-left:.8em;color:#3a4859;
       font-style:italic;margin:.5em 0}
.task{border:1px solid #dfe5ec;border-radius:8px;padding:1em 1.2em;margin:1em 0}
.task h3{margin:0 0 .4em;font-size:1em}
.task .why{margin:0 0 .7em}
.es{white-space:pre-wrap;background:#fbfcfd;border:1px dashed #c3ccd8;
    border-radius:6px;padding:.7em .9em}
.eslabel{font-size:.78em;color:#5b6b7f;text-transform:uppercase;
         letter-spacing:.05em;margin-bottom:.3em}
footer{margin-top:2.5em;color:#5b6b7f;font-size:.82em;border-top:1px solid #dfe5ec;
       padding-top:.8em}
@media print{body{padding:0}}
"""


def build(*, student: str, assignment: str, placement, findings, drills) -> str:
    """Return a complete HTML document for one student."""
    e = html.escape
    limiting = placement.limiting_criterion
    focus = next((f for f in findings if f.criterion == limiting), None)

    parts = [
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>",
        f"<title>Feedback for {e(student)}</title><style>{CSS}</style>",
        "</head><body>",
        f"<h1>Feedback for {e(student)}</h1>",
        f"<p class='meta'>{e(assignment)} &middot; {date.today():%d %B %Y}</p>",
    ]

    if focus is not None:
        parts += [
            "<div class='focus'>",
            f"<b>What to work on next:</b> {e(FOCUS_NAMES.get(limiting, limiting))}.",
            f"<p>{e(focus.ceiling_reason)}</p>",
            "</div>",
        ]
        if focus.evidence:
            parts.append("<h2>From your own writing</h2>")
            for ev in focus.evidence[:3]:
                parts.append(f"<div class='quote'>“{e(ev.quote)}”</div>")
                parts.append(f"<p>{e(ev.observation)}</p>")

    parts.append("<h2>Practice</h2>")
    for d in drills.drills:
        kind = "Writing" if d.kind == "essay_prompt" else "Exercise"
        parts += [
            "<div class='task'>",
            f"<h3>{kind}: {e(d.title)}</h3>",
            f"<p class='why'>{e(d.explanation_en)}</p>",
            "<div class='eslabel'>En español</div>",
            f"<div class='es'>{e(d.task_es)}</div>",
            "</div>",
        ]

    parts += [
        "<footer>This feedback is based on a single piece of writing. It is ",
        "not a grade or an official level — it is a suggestion about what to ",
        "practise next.</footer>",
        "</body></html>",
    ]
    return "\n".join(parts)
