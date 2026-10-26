"""Streamlit front end.

    streamlit run app/main.py

Built around what a teacher actually does: work through a stack of papers,
one student at a time, and keep what the app said so it can be looked at
again next time.

Three screens per submission, and the middle one is a safety control rather
than a convenience:

    1. Choose the pages. Check which way up they are.
    2. CONFIRM THE TRANSCRIPT. Measured failures make this load-bearing --
       the transcriber has misread `entonces` as `entonses` and had the
       error graded as the student's, and on an upside-down page it
       returned an entirely invented composition at 98% confidence.
    3. The assessment, saved to disk, with a printable sheet for the student.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from app.config import (  # noqa: E402
    BLENDED_PRICE_PER_1M,
    MODEL,
    PRICING_IS_BLENDED,
    SAMPLES_DIR,
)
from backend import handout, imaging, pipeline, progress, scale, store  # noqa: E402
from backend.client import ContentFiltered  # noqa: E402
from backend.pipeline import Unreadable  # noqa: E402
from backend.usage import Ledger  # noqa: E402
import json  # noqa: E402

st.set_page_config(
    page_title="Entrenador de escritura",
    page_icon="✎",
    layout="wide",
    # Everything that starts a task lives in the sidebar, so collapsing
    # it by default hides the way in.
    initial_sidebar_state="expanded",
)

CRITERION_LABEL = {
    "F": "Functions & tasks",
    "A": "Accuracy",
    "C": "Context & content",
    "T": "Text type",
}

st.markdown(
    """
    <style>
      /* Source Serif 4: a warm transitional serif designed for screen, in the
         same family of shapes as the serif Claude's own interface uses. The
         stack falls back to Georgia so the app still reads correctly if the
         font cannot be fetched. */
      @import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,opsz,wght@0,8..60,300..700;1,8..60,300..600&display=swap');

      :root{
        /* Spanish and Latin American ceramics: warm paper, terracotta,
           saffron, olive, and a brown-black ink instead of a cold grey. */
        --paper:#FCF8F2; --paper-2:#F6EEE2; --paper-3:#F0E4D2;
        --ink:#2A211C; --muted:#7A6A5D; --line:#E4D6C3;
        --terra:#B4542E; --terra-soft:#F7E7DE;
        --saffron:#C98A1E; --saffron-soft:#FBF0D8;
        --olive:#5C7A4A; --olive-soft:#EBF1E5;
        --brick:#A33327; --brick-soft:#FAE6E2;
        --serif:'Source Serif 4', Georgia, 'Iowan Old Style', 'Times New Roman', serif;
      }

      html, body, .stApp, [class*="css"]{font-family:var(--serif)!important;}
      .stApp{background:var(--paper);}
      .block-container{padding-top:1.5rem; max-width:1280px;}

      h1,h2,h3,h4{font-family:var(--serif)!important; color:var(--ink);
        letter-spacing:-.01em; font-weight:600;}
      h1{font-size:2.15rem!important; letter-spacing:-.02em;}
      h2{font-size:1.28rem!important;}
      h3{font-size:1.06rem!important;}
      p, li, label, span, div{font-family:var(--serif);}

      section[data-testid="stSidebar"]{background:var(--paper-2);
        border-right:1px solid var(--line);}
      section[data-testid="stSidebar"] .block-container{padding-top:1.2rem;}

      /* The headline placement: warm clay rather than navy. */
      .levelcard{background:linear-gradient(135deg,#8C3F22 0%,#B4542E 55%,#C2763F 100%);
        color:#FFF8F1; padding:1.2rem 1.45rem; border-radius:14px;
        margin-bottom:.55rem; box-shadow:0 8px 20px rgba(140,63,34,.22);}
      .levelcard h2{margin:0!important; font-size:1.8rem!important; color:#FFF8F1!important;
        letter-spacing:-.02em;}
      .levelcard p{margin:.3rem 0 0; opacity:.9; font-size:.92rem;}

      .steps{display:flex; gap:.4rem; margin:.1rem 0 1rem;}
      .step{flex:1; font-size:.72rem; font-weight:600; letter-spacing:.04em;
        text-transform:uppercase; color:var(--muted); padding:.44rem .6rem;
        border-radius:8px; background:var(--paper-2); border:1px solid var(--line);
        text-align:center;}
      .step.on{background:var(--terra); border-color:var(--terra); color:#FFF8F1;}
      .step.done{background:var(--olive-soft); border-color:#C8D9BC; color:var(--olive);}

      .pill{display:inline-block; padding:.2rem .68rem; border-radius:999px;
        font-size:.74rem; font-weight:600; margin:0 .35rem .3rem 0;
        border:1px solid transparent;}
      .ok{background:var(--olive-soft); color:var(--olive); border-color:#C8D9BC;}
      .warn{background:var(--brick-soft); color:var(--brick); border-color:#EEC4BC;}

      .subtitle{margin:-.55rem 0 .5rem; color:var(--terra); font-size:1.02rem;
        font-weight:600; letter-spacing:.04em; text-transform:uppercase;}
      .muted{color:var(--muted); font-size:.86rem; line-height:1.55;}
      .quote{border-left:3px solid var(--terra); padding:.15rem 0 .15rem .8rem;
        color:#4A3A30; font-style:italic; margin:.45rem 0 .2rem;}

      div[data-testid="stExpander"]{border:1px solid var(--line);
        border-radius:10px; margin-bottom:.5rem; background:#FFFDFA;}
      div[data-testid="stExpander"] summary{font-size:.95rem;}

      div[data-testid="stMetricValue"]{font-size:1.55rem; letter-spacing:-.02em;
        color:var(--ink);}
      div[data-testid="stMetricLabel"]{color:var(--muted);}

      .stTabs [data-baseweb="tab-list"]{gap:1.4rem;
        border-bottom:1px solid var(--line);}
      .stTabs [data-baseweb="tab"]{font-size:.92rem; padding:.4rem .1rem;}

      .stButton button{border-radius:9px; font-weight:600;
        font-family:var(--serif);}

      code, pre, .stCode{font-family:ui-monospace,'SF Mono',Consolas,monospace!important;}
      /* Streamlit paints its alerts in cool blues and greys by default. */
      div[data-testid="stAlert"]{border-radius:10px; border:1px solid var(--line);}
      /* The progress bar and inline code chips are the last two places
         Streamlit paints its own blue and green into a warm page. */
      /* Streamlit's progress-bar internals are unlabelled divs whose nesting
         changes between versions, so colour every descendant of the bar and
         let the track's own background show through underneath. */
      [role="progressbar"] div{background-color:var(--terra)!important;}
      [role="progressbar"]{background-color:var(--paper-3)!important;
        border-radius:999px;}
      code{background:var(--paper-3)!important; color:#6B3A22!important;
        padding:.05rem .3rem; border-radius:4px;}
    </style>
    """,
    unsafe_allow_html=True,
)


def note(text: str) -> None:
    """A warm informational callout.

    Streamlit's st.info is a fixed cold blue, and its alert variants cannot
    be told apart in CSS without depending on generated class names that
    change between releases. st.warning and st.error are left alone -- amber
    and red still read correctly against this palette, and they carry real
    urgency that should not be softened.
    """
    st.markdown(
        '<div style="background:var(--saffron-soft);border:1px solid #E8D4A6;'
        'border-left:4px solid var(--saffron);border-radius:0 9px 9px 0;'
        'padding:.75rem 1rem;margin:.35rem 0 .9rem;color:#5B4A2A;'
        f'font-size:.92rem;line-height:1.55;">{text}</div>',
        unsafe_allow_html=True,
    )


def stepper(active: int) -> None:
    """Show which of the three stages the teacher is in."""
    names = ["1 · Read the page", "2 · Check the transcript", "3 · Assessment"]
    cells = []
    for i, name in enumerate(names, 1):
        cls = "step on" if i == active else ("step done" if i < active else "step")
        cells.append(f'<div class="{cls}">{name}</div>')
    st.markdown(f'<div class="steps">{"".join(cells)}</div>', unsafe_allow_html=True)


def manifest() -> dict:
    p = SAMPLES_DIR / "manifest.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {
        "prompt_es": "", "samples": []
    }


def reset() -> None:
    for k in ("res", "stage", "pages", "rotation", "axis_clear", "saved_to"):
        st.session_state.pop(k, None)


# --------------------------------------------------------------------------
# Sidebar
# --------------------------------------------------------------------------
st.sidebar.title("✎ Entrenador de escritura")
st.sidebar.caption(f"ACTFL Writing Coach · 2024 descriptors · {MODEL}")

VIEWS = ["Assess", "Progress", "History"]
# The view is mirrored in the URL so a teacher can bookmark the progress
# screen, and so it can be opened directly rather than only by clicking.
_q = st.query_params.get("view", "Assess")
view = st.sidebar.radio(
    "View",
    VIEWS,
    index=VIEWS.index(_q) if _q in VIEWS else 0,
    horizontal=True,
    label_visibility="collapsed",
)
if st.query_params.get("view") != view:
    st.query_params["view"] = view

mf = manifest()

if view == "Assess":
    student = st.sidebar.text_input("Student", placeholder="e.g. Javier R.")
    source = st.sidebar.radio("Pages", ["Upload photos", "Bundled sample"])

    pages: list[bytes] = []
    source_label = ""
    if source == "Upload photos":
        ups = st.sidebar.file_uploader(
            "Photograph each page",
            type=["png", "jpg", "jpeg"],
            accept_multiple_files=True,
            on_change=reset,
        )
        if ups:
            pages = [u.read() for u in ups]
            source_label = ", ".join(u.name for u in ups)
    else:
        ids = [s["id"] for s in mf["samples"]]
        if ids:
            chosen = st.sidebar.selectbox("Sample", ids, on_change=reset)
            pages = [(SAMPLES_DIR / f"{chosen}.png").read_bytes()]
            source_label = chosen
            if not student:
                student = chosen

    default_prompt = next(
        (s.get("prompt") for s in mf["samples"]
         if s["id"] == source_label and s.get("prompt")),
        mf.get("prompt_es", ""),
    )
    assignment = st.sidebar.text_area(
        "Assignment the student was set", value=default_prompt, height=100
    )

    st.sidebar.divider()
    if st.sidebar.button("Start over", use_container_width=True):
        reset()
        st.rerun()

# --------------------------------------------------------------------------
# Progress view -- one student across submissions
# --------------------------------------------------------------------------
if view == "Progress":
    st.title("Progress")
    st.caption(
        "A single composition cannot establish an ACTFL rating. Several, "
        "over time, can show whether the gap the app named actually closed — "
        "which is the question a teacher is really asking."
    )
    names = store.students()
    if not names:
        note("No saved assessments yet.")
        st.stop()

    who = st.selectbox("Student", names)
    s = progress.summary(who)
    if not s["enough"]:
        note(
            f"{who} has {len(s['points'])} saved assessment(s). "
            "At least two are needed to show movement."
        )
        st.stop()

    first, last = s["first"], s["last"]
    m = st.columns(4)
    m[0].metric("Submissions", s["n"])
    m[1].metric(
        "Sublevels moved",
        f"{s['overall_delta']:+d}",
        delta=f"{first.overall} → {last.overall}",
    )
    m[2].metric(
        "Targeted gaps closed", f"{s['closed_count']}/{s['targeted_count']}"
    )
    # Short form: the full criterion name truncates in a narrow metric.
    SHORT = {"F": "Functions", "A": "Accuracy", "C": "Content", "T": "Text type"}
    m[3].metric("Bottleneck now", SHORT.get(last.limiting, last.limiting or "?"))

    st.warning(
        "**Read these as the app's own movement, not as certified progress.** "
        "The app places about 1.5–2 sublevels low. A roughly constant bias "
        "largely cancels when you subtract two measurements taken the same "
        "way, which is why change is more trustworthy here than level — but "
        "the bias widens at higher proficiency, so a student improving across "
        "that range will have their gain understated."
    )

    import pandas as pd

    rows = progress.chart_rows(s["points"])
    df = pd.DataFrame(
        {CRITERION_LABEL[c]: rows[c] for c in progress.CRITERIA},
        index=[p.saved_at[:10] for p in s["points"]],
    )
    st.line_chart(df, height=300)
    st.caption(
        "Vertical axis is the ACTFL sublevel ladder: "
        + ", ".join(
            f"{i}={scale.label(*scale.ORDER[i])}" for i in range(0, 7)
        )
        + " …"
    )

    st.subheader("What changed, step by step")
    for i, step in enumerate(s["steps"], 1):
        before, after = s["points"][i - 1], s["points"][i]
        targeted = next((mv for mv in step if mv.was_limiting), None)
        if targeted is None:
            verdict = "No criterion was flagged as limiting in the earlier run."
        elif targeted.closed:
            verdict = (
                f"**The targeted gap closed.** "
                f"{CRITERION_LABEL[targeted.criterion]} was the bottleneck and "
                f"moved {targeted.before} → {targeted.after}."
            )
        else:
            verdict = (
                f"**The targeted gap did not move.** "
                f"{CRITERION_LABEL[targeted.criterion]} was the bottleneck and "
                f"stayed at {targeted.before}."
            )
        with st.expander(
            f"{before.saved_at[:10]} → {after.saved_at[:10]} · "
            f"{before.overall} → {after.overall}",
            expanded=(i == len(s["steps"])),
        ):
            st.markdown(verdict)
            cols = st.columns(4)
            short = {"F": "Functions", "A": "Accuracy", "C": "Content",
                     "T": "Text type"}
            for col, mv in zip(cols, step):
                col.metric(
                    short[mv.criterion] + (" ★" if mv.was_limiting else ""),
                    mv.after,
                    delta=f"{mv.delta:+d}" if mv.delta else "no change",
                )
            st.caption("★ marks the criterion the previous drills targeted.")

    if s["bottleneck_moved"]:
        st.success(
            f"The bottleneck moved from "
            f"{CRITERION_LABEL.get(first.limiting, first.limiting)} to "
            f"{CRITERION_LABEL.get(last.limiting, last.limiting)}. A bottleneck "
            "that shifts is usually good news: the old constraint stopped "
            "being the binding one."
        )
    else:
        note(
            f"{CRITERION_LABEL.get(last.limiting, last.limiting)} has been the "
            f"bottleneck throughout. If the practice is not shifting it, the "
            "drills for this criterion are the thing to change."
        )
    st.stop()

# --------------------------------------------------------------------------
# History view
# --------------------------------------------------------------------------
if view == "History":
    st.title("Saved assessments")
    runs = store.history()
    if not runs:
        note("Nothing saved yet. Assess a composition and it will appear here.")
        st.stop()

    names = ["Everyone"] + store.students()
    who = st.selectbox("Student", names)
    shown = runs if who == "Everyone" else [r for r in runs if r["student"] == who]

    st.caption(f"{len(shown)} assessment(s)")
    for r in shown:
        p = r.get("placement") or {}
        level = f"{p.get('consistent_with_level','?')} {p.get('consistent_with_sublevel') or ''}".strip()
        with st.expander(
            f"**{r['student']}** — {level} · limited by "
            f"{CRITERION_LABEL.get(p.get('limiting_criterion',''), '?')} "
            f"· {r['saved_at'][:16].replace('T',' ')}"
        ):
            st.caption(r.get("assignment", ""))
            st.text(r.get("transcript", ""))
            cols = st.columns(4)
            cols[0].metric("Quotes verified", f"{r['quotes_verified']}/{r['quotes_total']}")
            cols[1].metric("Injection spans", len(r.get("injection_hits", [])))
            cols[2].metric("Tokens", f"{r['ledger']['prompt_tokens'] + r['ledger']['completion_tokens']:,}")
            cols[3].metric("Cost", f"${r['ledger']['cost_usd']:.4f}")
            for f in r.get("findings", []):
                st.markdown(
                    f"**{f['criterion']}** — {f['consistent_with_level']} "
                    f"{f.get('consistent_with_sublevel') or ''}: {f['ceiling_reason']}"
                )
    st.stop()

# --------------------------------------------------------------------------
# Assess view
# --------------------------------------------------------------------------
st.title("Entrenador de escritura")
st.markdown(
    '<p class="subtitle">ACTFL Writing Coach</p>', unsafe_allow_html=True
)
st.caption(
    "Reads handwritten Spanish, reports the evidence it shows against the "
    "ACTFL 2024 Writing descriptors, and builds practice aimed at whatever is "
    "blocking the next sublevel."
)

if not pages:
    note("Add one or more page photos in the sidebar to begin.")
    st.stop()

# Orientation: the axis is detected, the flip is the teacher's call.
if "rotation" not in st.session_state:
    cands, scores = imaging.suggest_rotations(pages[0])
    st.session_state.rotation = cands[0]
    st.session_state.axis_clear = imaging.axis_is_clear(scores)
rotation = st.session_state.rotation

left, right = st.columns([1, 1.3], gap="large")

with left:
    idx = 0
    if len(pages) > 1:
        idx = st.number_input(
            "Page", 1, len(pages), 1, help=f"{len(pages)} pages in this submission"
        ) - 1
    st.image(
        imaging.rotate(imaging.load(pages[idx]), rotation),
        caption=f"Page {idx + 1} of {len(pages)} · rotated {rotation}°",
        use_container_width=True,
    )
    c1, c2, c3 = st.columns(3)
    # Short labels: the three buttons share a narrow column and "180°" with
    # a symbol in front of it truncates to "1...".
    for col, label, delta in ((c1, "↺ 90", -90), (c2, "↻ 90", 90), (c3, "Flip", 180)):
        if col.button(label, use_container_width=True):
            st.session_state.rotation = (rotation + delta) % 360
            st.session_state.manual_rotation = st.session_state.rotation
            st.session_state.pop("res", None)
            st.session_state.stage = "new"
            st.rerun()
    if not st.session_state.get("axis_clear", True):
        st.warning(
            "Could not work out which way up this page goes — check it reads "
            "correctly above before transcribing."
        )

stage = st.session_state.get("stage", "new")

with right:
    # --- stage 1 ----------------------------------------------------------
    if stage == "new":
        stepper(1)
        st.subheader("Read the handwriting")
        st.markdown(
            '<span class="muted">The transcription is deliberately literal: '
            "spelling errors, missing accents and wrong verb forms are kept "
            "exactly as written, because those errors are the evidence being "
            "assessed. The orientation is worked out automatically; if the "
            "page cannot be read, the app says so rather than guessing at "
            "it.</span>",
            unsafe_allow_html=True,
        )
        if st.button("Transcribe", type="primary", disabled=not assignment.strip()):
            try:
                with st.spinner(f"Reading {len(pages)} page(s)..."):
                    res = pipeline.RunResult(ledger=Ledger(label=student or "ui"))
                    pipeline.transcribe_step(
                        raw_images=pages,
                        # None lets the app find the orientation itself; the
                        # rotate buttons set an explicit angle.
                        rotation=st.session_state.get("manual_rotation"),
                        res=res,
                    )
            except ContentFiltered as exc:
                st.error(str(exc))
                st.stop()
            st.session_state.res = res
            st.session_state.rotation = res.rotation_applied
            st.session_state.stage = "confirm"
            st.rerun()
        if not assignment.strip():
            st.caption(
                "Add the assignment the student was set — without it, "
                "Functions and tasks is judged against nothing."
            )

    # --- stage 2 ----------------------------------------------------------
    elif stage == "confirm":
        res = st.session_state.res
        stepper(2)
        st.subheader("Check the transcript")
        st.markdown(
            '<span class="muted">Read this against the image, line by line. '
            "Two measured failures make this step load-bearing: "
            "<code>entonces</code> was read as <code>entonses</code> and then "
            "graded as the student's spelling mistake; and on an upside-down "
            "page the model returned an <b>entirely invented composition</b> "
            "at 98% confidence. If this does not match the page, fix it or "
            "rotate and re-read.</span>",
            unsafe_allow_html=True,
        )

        if res.injection_hits:
            st.error(
                f"**Prompt injection blocked — {len(res.injection_hits)} span(s).** "
                "This composition contains text addressed to the grading system. "
                "It is being treated as student writing, not as an instruction."
            )
            for h in res.injection_hits:
                st.code(h.excerpt, language=None)

        if res.unreadable:
            st.error(
                "**The page could not be read.** The app tried "
                f"{len(res.orientation_attempts)} orientation(s) and reported "
                "it could not make out the writing, rather than guessing at "
                "it. Rotate the page, re-photograph it in better light, or "
                "type the text in below and it will be assessed on that."
            )
            st.caption(f"Attempts (rotation, confidence): {res.orientation_attempts}")

        conf = res.transcript.confidence
        st.progress(conf, text=f"Transcription confidence {conf:.0%}")
        if res.transcript.illegible_spans:
            st.warning("Unreadable: " + ", ".join(res.transcript.illegible_spans))

        edited = st.text_area("Transcript", value=res.transcript_text, height=260)
        a, b = st.columns(2)
        if a.button("Looks right — assess it", type="primary"):
            res.human_edited = edited.strip() != res.transcript.text.strip()
            res.transcript_text = edited
            try:
                with st.spinner("Four criterion specialists are reading it..."):
                    pipeline.assess_step(prompt_text=assignment, res=res)
            except Unreadable as exc:
                st.error(str(exc))
                st.stop()
            st.session_state.res = res
            st.session_state.saved_to = store.save(
                res, student=student or "sin nombre",
                assignment=assignment, source=source_label,
            ).name
            st.session_state.stage = "done"
            st.rerun()
        if b.button("Re-read the page"):
            st.session_state.stage = "new"
            st.rerun()

    # --- stage 3 ----------------------------------------------------------
    else:
        res = st.session_state.res
        p = res.placement
        stepper(3)
        st.markdown(
            f'<div class="levelcard"><h2>Consistent with '
            f"{p.consistent_with_level} {p.consistent_with_sublevel or ''}</h2>"
            f"<p>Limited by <b>{CRITERION_LABEL[p.limiting_criterion]}</b> "
            f"· next rung: {p.next_sublevel_target}</p></div>",
            unsafe_allow_html=True,
        )
        st.caption(p.caveat)
        st.warning(
            "**Calibration note.** Measured against expert raters, this app "
            "places about 1.5–2 ACTFL sublevels low, and the gap widens at "
            "higher proficiency. Use the limiting criterion and the practice; "
            "do not report this level to a student or a record."
        )
        if res.human_edited:
            st.caption("Assessed on a human-corrected transcript.")
        if st.session_state.get("saved_to"):
            st.caption(f"Saved as {st.session_state.saved_to}")

if stage != "done":
    st.stop()

# --------------------------------------------------------------------------
# Results
# --------------------------------------------------------------------------
res = st.session_state.res
p = res.placement
tabs = st.tabs(
    ["FACT breakdown", "Targeted practice", "For the student", "Agent trace",
     "Safety", "Cost"]
)

with tabs[0]:
    st.write(p.rationale)
    for f in res.findings:
        blocking = " ← blocking" if f.criterion == p.limiting_criterion else ""
        with st.expander(
            f"**{f.criterion} · {CRITERION_LABEL[f.criterion]}** — consistent with "
            f"{f.consistent_with_level} {f.consistent_with_sublevel or ''}{blocking}",
            expanded=f.criterion == p.limiting_criterion,
        ):
            st.markdown(f"**What is blocking the next sublevel:** {f.ceiling_reason}")
            for e in f.evidence:
                st.markdown(
                    f'<div class="quote">“{e.quote}”</div>'
                    f'<div class="muted">{e.observation}</div>',
                    unsafe_allow_html=True,
                )

with tabs[1]:
    st.markdown(
        f"Aimed at **{CRITERION_LABEL[p.limiting_criterion]}**, the criterion "
        f"holding this student below {p.next_sublevel_target}."
    )
    for d in res.drills.drills:
        kind = "Essay prompt" if d.kind == "essay_prompt" else "Technical drill"
        with st.expander(f"**{kind} · {d.title}**", expanded=True):
            st.markdown("**For the student** (English — they are still "
                        "learning Spanish)")
            st.write(d.explanation_en)
            st.markdown("**The task itself** (Spanish)")
            st.code(d.task_es, language=None, wrap_lines=True)
            st.markdown("**Teacher note**")
            st.caption(d.teacher_note_en)

with tabs[2]:
    st.markdown(
        "A one-page sheet written to the student. It shows the single "
        "criterion to work on and the practice for it — **no level**, because "
        "the measured calibration does not support putting one in front of a "
        "student."
    )
    sheet = handout.build(
        student=student or "Estudiante",
        assignment=assignment,
        placement=p,
        findings=res.findings,
        drills=res.drills,
    )
    st.download_button(
        "Download the student's sheet (HTML)",
        data=sheet,
        file_name=f"comentarios_{(student or 'estudiante').replace(' ', '_')}.html",
        mime="text/html",
        type="primary",
    )
    st.components.v1.html(sheet, height=520, scrolling=True)

with tabs[3]:
    st.markdown(
        '<span class="muted">Every agent that ran, in order.</span>',
        unsafe_allow_html=True,
    )
    for i, step in enumerate(res.trace, 1):
        icon = "🛑" if step.blocked else "•"
        with st.expander(
            f"{icon} **{i}. {step.agent}** — {step.summary}  ({step.seconds:.1f}s)"
        ):
            if isinstance(step.detail, str):
                st.text(step.detail)
            else:
                st.json(step.detail)

with tabs[4]:
    bad = [q for q in res.quote_checks if not q.found]
    def badge(ok: bool, text: str) -> str:
        return f'<span class="pill {"ok" if ok else "warn"}">{text}</span>'

    st.markdown(
        badge(not res.injection_hits, f"injection: {len(res.injection_hits)} blocked")
        + badge(not bad, f"quotes: {len(res.quote_checks) - len(bad)}/{len(res.quote_checks)} verified")
        + badge(not res.over_claims, f"over-claims: {len(res.over_claims)}"),
        unsafe_allow_html=True,
    )
    st.divider()
    st.markdown(
        "**Injection** — the transcript is scanned in plain Python before any "
        "agent reasons about it. Patterns key on the parts of an attack that "
        "survive handwriting OCR: a real attack reading `IGNORA LAS "
        "INSTRUCCIONES` was transcribed as `Estoy las instrucciones`, and "
        "anything keyed on the verb missed it."
    )
    for h in res.injection_hits:
        st.code(h.excerpt, language=None)
    st.markdown(
        "**Fabricated quotes** — every piece of evidence must quote the "
        "transcript verbatim, checked by string containment rather than by "
        "asking a model."
    )
    for q in bad:
        st.error(f"[{q.criterion}] not in transcript: {q.quote!r}")
    st.markdown(
        "**Over-claiming** — ACTFL requires sustained performance across many "
        "situations before a level may be assigned, so a single sample can "
        "only show evidence."
    )
    for o in res.over_claims:
        st.error(o)

with tabs[5]:
    led = res.ledger
    c = st.columns(4)
    c[0].metric("Tokens in", f"{led.prompt_tokens:,}")
    c[1].metric("Served from cache", f"{led.cache_hit_rate:.1%}")
    c[2].metric("Tokens out", f"{led.completion_tokens:,}")
    c[3].metric("Cost this run", f"${led.cost_usd:.4f}")
    st.code(led.table(), language=None)
    per = led.cost_usd
    st.markdown(
        f"At four compositions per student per month: **\\${per * 4:.3f}** per "
        f"student, **\\${per * 4 * 30:,.2f}**/mo for a class of 30, "
        f"**\\${per * 4 * 10_000:,.0f}**/mo at 10,000."
    )
    if PRICING_IS_BLENDED:
        st.caption(
            f"Costed at a blended \\${BLENDED_PRICE_PER_1M}/1M tokens derived "
            "from this account's Portkey analytics; no per-token rate sheet is "
            "published for this model."
        )
