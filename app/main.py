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
from backend import handout, imaging, pipeline, store  # noqa: E402
from backend.client import ContentFiltered  # noqa: E402
from backend.usage import Ledger  # noqa: E402
import json  # noqa: E402

st.set_page_config(page_title="ACTFL Writing Coach", page_icon="✎", layout="wide")

CRITERION_LABEL = {
    "F": "Functions & tasks",
    "A": "Accuracy",
    "C": "Context & content",
    "T": "Text type",
}

st.markdown(
    """
    <style>
      .block-container {padding-top: 2rem; max-width: 1240px;}
      .levelcard {background:#0f1b2d;color:#fff;padding:1.1rem 1.4rem;
                  border-radius:12px;margin-bottom:.5rem;}
      .levelcard h2 {margin:0;font-size:1.7rem;color:#fff;}
      .levelcard p  {margin:.25rem 0 0;opacity:.78;font-size:.9rem;}
      .pill {display:inline-block;padding:.12rem .6rem;border-radius:999px;
             font-size:.72rem;font-weight:600;margin-right:.35rem;}
      .ok{background:#dcfce7;color:#14532d;} .warn{background:#fee2e2;color:#7f1d1d;}
      .muted{color:#64748b;font-size:.84rem;}
      .quote{border-left:3px solid #94a3b8;padding-left:.7rem;color:#334155;
             font-style:italic;margin:.3rem 0;}
    </style>
    """,
    unsafe_allow_html=True,
)


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
st.sidebar.title("✎ Writing Coach")
st.sidebar.caption(f"ACTFL 2024 · Writing · {MODEL}")

view = st.sidebar.radio("", ["Assess", "History"], horizontal=True, label_visibility="collapsed")

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
# History view
# --------------------------------------------------------------------------
if view == "History":
    st.title("Saved assessments")
    runs = store.history()
    if not runs:
        st.info("Nothing saved yet. Assess a composition and it will appear here.")
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
st.title("ACTFL Writing Coach")
st.caption(
    "Reads handwritten Spanish, reports the evidence it shows against the "
    "ACTFL 2024 Writing descriptors, and builds practice aimed at whatever is "
    "blocking the next sublevel."
)

if not pages:
    st.info("Add one or more page photos in the sidebar to begin.")
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
    for col, label, delta in ((c1, "↺ 90°", -90), (c2, "↻ 90°", 90), (c3, "↕ 180°", 180)):
        if col.button(label, use_container_width=True):
            st.session_state.rotation = (rotation + delta) % 360
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
        st.subheader("Step 1 · Read the handwriting")
        st.markdown(
            '<span class="muted">The transcription is deliberately literal: '
            "spelling errors, missing accents and wrong verb forms are kept "
            "exactly as written, because those errors are the evidence being "
            "assessed. Check the page is the right way up first — the model "
            "will invent a plausible composition rather than admit it cannot "
            "read one.</span>",
            unsafe_allow_html=True,
        )
        if st.button("Transcribe", type="primary", disabled=not assignment.strip()):
            try:
                with st.spinner(f"Reading {len(pages)} page(s)..."):
                    res = pipeline.RunResult(ledger=Ledger(label=student or "ui"))
                    pipeline.transcribe_step(
                        raw_images=pages, rotation=rotation, res=res
                    )
            except ContentFiltered as exc:
                st.error(str(exc))
                st.stop()
            st.session_state.res = res
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
        st.subheader("Step 2 · Check the transcript")
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

        conf = res.transcript.confidence
        st.progress(conf, text=f"Model's own confidence {conf:.0%} (not reliable alone)")
        if res.transcript.illegible_spans:
            st.warning("Unreadable: " + ", ".join(res.transcript.illegible_spans))

        edited = st.text_area("Transcript", value=res.transcript_text, height=260)
        a, b = st.columns(2)
        if a.button("Looks right — assess it", type="primary"):
            res.human_edited = edited.strip() != res.transcript.text.strip()
            res.transcript_text = edited
            with st.spinner("Four criterion specialists are reading it..."):
                pipeline.assess_step(prompt_text=assignment, res=res)
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
            st.markdown("**Para el estudiante**")
            st.write(d.instructions_es)
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
