"""Streamlit front end.

    streamlit run app/main.py

Three screens, in order, because the middle one is a safety control rather
than a convenience:

    1. Choose a composition (upload a photo, or pick a bundled sample).
    2. CONFIRM THE TRANSCRIPT. The teacher reads what the model read and
       fixes it. Measured on the fixtures, the transcriber turned "entonces"
       into "entonses" and the Accuracy agent then graded the student on the
       misreading. Nothing is assessed until a human has seen this screen.
    3. The assessment: FACT breakdown, what is blocking the next sublevel,
       targeted practice, the full agent trace, and live token cost.
"""

from __future__ import annotations

import base64
import json
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
from backend import pipeline  # noqa: E402
from backend.usage import Ledger  # noqa: E402

st.set_page_config(page_title="ACTFL Writing Coach", page_icon="✎", layout="wide")

LEVEL_ORDER = ["Novice", "Intermediate", "Advanced", "Superior", "Distinguished"]
CRITERION_LABEL = {
    "F": "Functions & tasks",
    "A": "Accuracy",
    "C": "Context & content",
    "T": "Text type",
}

st.markdown(
    """
    <style>
      .block-container {padding-top: 2.2rem; max-width: 1180px;}
      .levelcard {background:#0f1b2d;color:#fff;padding:1.1rem 1.4rem;
                  border-radius:12px;margin-bottom:.6rem;}
      .levelcard h2 {margin:0;font-size:1.75rem;color:#fff;}
      .levelcard p  {margin:.25rem 0 0;opacity:.78;font-size:.9rem;}
      .pill {display:inline-block;padding:.12rem .6rem;border-radius:999px;
             font-size:.72rem;font-weight:600;margin-right:.35rem;}
      .ok   {background:#dcfce7;color:#14532d;}
      .warn {background:#fee2e2;color:#7f1d1d;}
      .muted{color:#64748b;font-size:.84rem;}
      .quote{border-left:3px solid #94a3b8;padding-left:.7rem;color:#334155;
             font-style:italic;margin:.3rem 0;}
    </style>
    """,
    unsafe_allow_html=True,
)


def data_url(raw: bytes, mime: str = "image/png") -> str:
    return f"data:{mime};base64," + base64.b64encode(raw).decode()


def manifest() -> dict:
    path = SAMPLES_DIR / "manifest.json"
    if not path.exists():
        return {"prompt_es": "", "samples": []}
    return json.loads(path.read_text(encoding="utf-8"))


def reset() -> None:
    for k in ("res", "stage", "image_bytes"):
        st.session_state.pop(k, None)


# --------------------------------------------------------------------------
# Sidebar: input
# --------------------------------------------------------------------------
st.sidebar.title("✎ Writing Coach")
st.sidebar.caption(f"ACTFL 2024 · Writing · {MODEL}")

mf = manifest()
mode = st.sidebar.radio("Composition", ["Bundled sample", "Upload a photo"])

image_bytes: bytes | None = None
if mode == "Bundled sample":
    ids = [s["id"] for s in mf["samples"]]
    if ids:
        chosen = st.sidebar.selectbox("Sample", ids, on_change=reset)
        image_bytes = (SAMPLES_DIR / f"{chosen}.png").read_bytes()
    else:
        st.sidebar.warning("No samples. Run: python scripts/make_samples.py")
else:
    up = st.sidebar.file_uploader(
        "Photo of handwritten work", type=["png", "jpg", "jpeg"], on_change=reset
    )
    if up:
        image_bytes = up.read()

prompt_text = st.sidebar.text_area(
    "Assignment prompt given to the student",
    value=mf.get("prompt_es", ""),
    height=90,
)

st.sidebar.divider()
if st.sidebar.button("Start over", use_container_width=True):
    reset()
    st.rerun()

# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
st.title("ACTFL Writing Coach")
st.caption(
    "Reads handwritten Spanish, reports the evidence it shows against the "
    "ACTFL 2024 Writing descriptors, and builds practice aimed at whatever is "
    "blocking the next sublevel."
)

if image_bytes is None:
    st.info("Pick a sample or upload a photo in the sidebar to begin.")
    st.stop()

left, right = st.columns([1, 1.25], gap="large")
with left:
    st.image(image_bytes, caption="Submission", use_container_width=True)

stage = st.session_state.get("stage", "new")

# --- stage 1: transcribe ---------------------------------------------------
with right:
    if stage == "new":
        st.subheader("Step 1 · Read the handwriting")
        st.markdown(
            '<span class="muted">The transcription is deliberately literal: '
            "spelling errors, missing accents and wrong verb forms are kept "
            "exactly as written, because those errors are the evidence being "
            "assessed.</span>",
            unsafe_allow_html=True,
        )
        if st.button("Transcribe", type="primary"):
            with st.spinner("Reading the page..."):
                res = pipeline.RunResult(ledger=Ledger(label="ui"))
                pipeline.transcribe_step(
                    image_data_url=data_url(image_bytes), res=res
                )
            st.session_state.res = res
            st.session_state.stage = "confirm"
            st.rerun()

    # --- stage 2: human confirms ------------------------------------------
    elif stage == "confirm":
        res = st.session_state.res
        st.subheader("Step 2 · Check the transcript")
        st.markdown(
            '<span class="muted">Read this against the image and fix anything '
            "misread. This step exists because a misread word becomes a "
            "fabricated student error: in testing, <code>entonces</code> was "
            "read as <code>entonses</code> and then graded as a spelling "
            "mistake.</span>",
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
        st.progress(conf, text=f"Transcription confidence {conf:.0%}")
        if res.transcript.illegible_spans:
            st.warning("Unreadable: " + ", ".join(res.transcript.illegible_spans))

        edited = st.text_area("Transcript", value=res.transcript_text, height=240)

        c1, c2 = st.columns(2)
        if c1.button("Looks right — assess it", type="primary"):
            res.human_edited = edited.strip() != res.transcript.text.strip()
            res.transcript_text = edited
            with st.spinner("Four criterion specialists are reading it..."):
                pipeline.assess_step(prompt_text=prompt_text, res=res)
            st.session_state.res = res
            st.session_state.stage = "done"
            st.rerun()
        if c2.button("Re-read the image"):
            st.session_state.stage = "new"
            st.rerun()

    # --- stage 3: results --------------------------------------------------
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
        if res.human_edited:
            st.caption("Assessed on a human-corrected transcript.")

if stage != "done":
    st.stop()

# --------------------------------------------------------------------------
# Results, full width
# --------------------------------------------------------------------------
res = st.session_state.res
p = res.placement

tabs = st.tabs(
    ["FACT breakdown", "Targeted practice", "Agent trace", "Safety", "Cost"]
)

with tabs[0]:
    st.write(p.rationale)
    for f in res.findings:
        limiting = " ← blocking" if f.criterion == p.limiting_criterion else ""
        with st.expander(
            f"**{f.criterion} · {CRITERION_LABEL[f.criterion]}** — consistent with "
            f"{f.consistent_with_level} {f.consistent_with_sublevel or ''}{limiting}",
            expanded=f.criterion == p.limiting_criterion,
        ):
            st.markdown(f"**What is blocking the next sublevel:** {f.ceiling_reason}")
            st.markdown("**Evidence from the text:**")
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
            st.caption(f"Targets {d.targets_criterion} — {d.targets_gap}")

with tabs[2]:
    st.markdown(
        '<span class="muted">Every agent that ran, in order, with what it '
        "produced and what it cost.</span>",
        unsafe_allow_html=True,
    )
    for i, step in enumerate(res.trace, 1):
        icon = "🛑" if step.blocked else "•"
        with st.expander(f"{icon} **{i}. {step.agent}** — {step.summary}  ({step.seconds:.1f}s)"):
            st.json(step.detail) if not isinstance(step.detail, str) else st.text(step.detail)

with tabs[3]:
    bad = [q for q in res.quote_checks if not q.found]
    badge = lambda ok, text: (  # noqa: E731
        f'<span class="pill {"ok" if ok else "warn"}">{text}</span>'
    )
    st.markdown(
        badge(not res.injection_hits, f"injection: {len(res.injection_hits)} blocked")
        + badge(not bad, f"quotes: {len(res.quote_checks) - len(bad)}/{len(res.quote_checks)} verified")
        + badge(not res.over_claims, f"over-claims: {len(res.over_claims)}"),
        unsafe_allow_html=True,
    )
    st.divider()
    st.markdown(
        "**Injection** — the composition is scanned in plain Python before any "
        "agent reasons about it. A guardrail written as a prompt can be argued "
        "out of running; this one cannot."
    )
    if res.injection_hits:
        for h in res.injection_hits:
            st.code(h.excerpt, language=None)
    st.markdown(
        "**Fabricated quotes** — every piece of evidence must quote the "
        "transcript verbatim, and each quote is checked by string containment, "
        "not by asking a model."
    )
    if bad:
        for q in bad:
            st.error(f"[{q.criterion}] not in transcript: {q.quote!r}")
    st.markdown(
        "**Over-claiming** — ACTFL requires sustained performance across many "
        "situations before a level may be assigned, so a single sample can only "
        "show evidence. Prose asserting a rating is flagged."
    )
    for o in res.over_claims:
        st.error(o)

with tabs[4]:
    led = res.ledger
    c = st.columns(4)
    c[0].metric("Tokens in", f"{led.prompt_tokens:,}")
    c[1].metric("Served from cache", f"{led.cache_hit_rate:.1%}")
    c[2].metric("Tokens out", f"{led.completion_tokens:,}")
    c[3].metric("Cost this run", f"${led.cost_usd:.4f}")
    st.code(led.table(), language=None)
    per_run = led.cost_usd
    st.markdown(
        f"At four compositions per student per month: "
        f"**${per_run * 4:.3f}** per student, "
        f"**${per_run * 4 * 100:,.2f}**/mo at 100 students, "
        f"**${per_run * 4 * 10_000:,.0f}**/mo at 10,000."
    )
    if PRICING_IS_BLENDED:
        st.caption(
            f"Costed at a blended ${BLENDED_PRICE_PER_1M}/1M tokens derived from "
            "this account's Portkey analytics ($29.72 over 34.1M tokens); no "
            "per-token rate sheet is published for this model. A blended rate "
            "cannot price caching separately, so the caching benefit is reported "
            "in tokens above rather than in dollars."
        )
