### The team

Seven agent calls per assessment, plus three deterministic checks that are
not agents at all.

| Agent | Job | Tools / input |
|---|---|---|
| **Transcriber** | Reads the page into text, preserving every error | Vision: one or more page images |
| **Eval F** | Functions and tasks | Transcript + the assignment the student was set |
| **Eval A** | Accuracy | Transcript |
| **Eval C** | Context and content | Transcript |
| **Eval T** | Text type | Transcript |
| **Adjudicator** | Synthesises four criterion findings into one placement | The four findings |
| **Drill generator** | Builds practice aimed at the limiting criterion | Placement + the four ceiling reasons |
| *Verifier* | Audits quotes and over-claiming | Transcript + claimed evidence |

Every agent returns a validated Pydantic object, never free text. Two
conventions run through all the schemas: each claim carries a `quote` copied
verbatim from the transcript, and the placement field is named
`consistent_with_level` so that writing an over-claiming sentence is awkward
by construction.

### How they are organised

![The pipeline. Four criterion specialists run in parallel; the human confirm step sits between transcription and assessment.](figures/architecture.png)

The shape is driven by the standard rather than by a preference for
multi-agent designs. ACTFL assesses four criteria that a writer can sit at
different levels on, and the *spread* between them is the diagnostic signal —
the weakest criterion is what blocks the next sublevel, and naming it is the
whole product. A single agent asked for all four at once flattens them toward
one impression.

That claim was tested rather than assumed. `scripts/compare_architectures.py`
runs both designs over the same transcripts: the combined call saves
{{"{:.0%}".format(f['arch']['saving'])}} but reaches a different placement in
{{f['arch']['n'] - f['arch']['same_placement']}} of {{f['arch']['n']}} samples
and disagrees on a third of individual criteria. See Tokenomics.

The human confirm step between transcription and assessment is a safety
control, not a convenience, and the reason is in Safety.

### Which model, and why

`gpt-6-luna` through Portkey, for all seven calls, with no fallback to
anything else. The course permits one model on the class key, so this is a
constraint rather than a choice — but it had a real consequence worth
recording: the whole project depends on the model accepting image input and
preserving Spanish diacritics, which was unknown at the start.
`scripts/check_vision.py` was therefore the first thing built, before any
pipeline code. It renders `¿Adónde fuiste ayer? Mi mamá compró el pañuelo.`
and checks the accents survive. They do.

The model name appears in exactly one file, `app/config.py`, and
`scripts/check_model_guard.py` fails the build if any other model identifier
turns up anywhere in the repository.

Two provider quirks cost real time and are documented in
`backend/model_provider.py`: this family rejects `max_tokens` in favour of
`max_completion_tokens`, and `reasoning_effort` must be pinned to `none` or
the model spends its entire output budget reasoning and returns empty
content.

### One real run, traced

![The transcript confirmation screen. The teacher reads what the model read before anything is graded.](figures/ui-confirm.png)

Submission: a short composition about a memorable day. The run trace, as the
app displays it:

| # | Agent | Result | Time |
|---|---|---|---|
| 1 | transcriber | 53 words, confidence 0.99 | 4.3 s |
| 2 | guardrail:injection | **BLOCKED** — 2 instruction-like spans found | 0.0 s |
| 3 | eval F/A/C/T | F=Novice High, A=Int Low, C=Int Low, T=Int Low | 5.1 s |
| 4 | guardrail:quotes | 12/12 verified | 0.0 s |
| 5 | adjudicator | consistent with Novice High, limited by F | 3.2 s |
| 6 | guardrail:over-claim | none | 0.0 s |
| 7 | drill_generator | 2 items targeting F | 4.8 s |

![The FACT breakdown. The blocking criterion is expanded by default, with the evidence quoted from the student's own text.](figures/ui-fact.png)

The four specialists disagreeing — F one sublevel below the other three — is
the case the architecture exists for. F is named as limiting, and the drill
generator is pointed at it rather than at general review.

![The run trace and per-agent token cost, as the app reports them.](figures/ui-cost.png)

### Getting the page in

Real photographs broke assumptions that typed fixtures never touched. A
landscape sheet shot by an upright phone has correct EXIF metadata and
vertical text, so two of the first three real sheets transcribed as
`[ilegible]`.

Orientation is now found by trying candidate rotations — ranked by an ink
projection profile, which identifies the axis reliably (2.97 against 0.35 on
a real page) — until the model reports it could read one. That loop was built,
abandoned and rebuilt: it only works because the transcriber will now admit
it cannot read a page. See Safety.

### Tracking a student over time

Each assessment is saved, and a progress view plots the four criteria across
a student's submissions, showing whether the criterion the app named as
limiting actually improved. This is the part of the design that answers
ACTFL's own objection to single-sample assessment, and the part the
calibration bias damages least.

![Four criteria tracked across one student's submissions. The app named a limiting criterion each time; this shows whether it moved.](figures/ui-progress.png)

### The deterministic layer

Three checks run in plain Python, not as prompts, because a guardrail written
as a prompt is vulnerable to the same attacks as the thing it guards:
injection scanning over the transcript, verbatim quote verification, and an
over-claim scan over the generated prose. They are described in Safety.
