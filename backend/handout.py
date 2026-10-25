"""The thing the student actually receives.

The app's own screen is built for the teacher: evidence, criteria, token
costs. None of that belongs on a page handed to a sixteen-year-old. This
builds a single self-contained HTML sheet the teacher can print or email,
written to the student, in a tone that says *here is your next step* rather
than *here is your rating*.

Three deliberate choices:

* **No level is shown to the student.** The app reads about 1.5 sublevels
  low against expert raters, so a level on a handout would be a number the
  measurements do not support. The teacher sees the placement and decides
  what, if anything, to say about it.
* **One focus, not four.** Only the limiting criterion and its practice
  appear. A list of everything wrong with your Spanish is not actionable.
* **The student's own words are quoted back**, because feedback anchored to
  something you actually wrote lands differently from a generic rule.
"""

from __future__ import annotations

import html
from datetime import date

CRITERION_NAMES = {
    "F": "what you can do in writing",
    "A": "accuracy",
    "C": "range of topics",
    "T": "how your writing is put together",
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
.es{white-space:pre-wrap}
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
        "<!doctype html><html lang='es'><head><meta charset='utf-8'>",
        f"<title>{e(student)} — comentarios</title><style>{CSS}</style>",
        "</head><body>",
        f"<h1>Comentarios para {e(student)}</h1>",
        f"<p class='meta'>{e(assignment)} &middot; {date.today():%d/%m/%Y}</p>",
    ]

    if focus is not None:
        parts += [
            "<div class='focus'>",
            f"<b>En qué concentrarte ahora:</b> {e(CRITERION_NAMES.get(limiting, limiting))}.",
            f"<p>{e(focus.ceiling_reason)}</p>",
            "</div>",
        ]
        if focus.evidence:
            parts.append("<h2>De tu propio texto</h2>")
            for ev in focus.evidence[:3]:
                parts.append(f"<div class='quote'>“{e(ev.quote)}”</div>")
                parts.append(f"<p>{e(ev.observation)}</p>")

    parts.append("<h2>Para practicar</h2>")
    for d in drills.drills:
        kind = "Escritura" if d.kind == "essay_prompt" else "Ejercicio"
        parts += [
            "<div class='task'>",
            f"<h3>{kind}: {e(d.title)}</h3>",
            f"<div class='es'>{e(d.instructions_es)}</div>",
            "</div>",
        ]

    parts += [
        "<footer>Estos comentarios se basan en una sola muestra de escritura. ",
        "No son una calificación ni un nivel oficial — son una indicación de ",
        "qué practicar después.</footer>",
        "</body></html>",
    ]
    return "\n".join(parts)
