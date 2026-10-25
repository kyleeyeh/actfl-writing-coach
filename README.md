# ACTFL Writing Coach

Photograph a student's handwritten Spanish composition. The app transcribes it
literally, reports which ACTFL 2024 Writing criteria the sample shows evidence
for, names the single criterion blocking the next sublevel, and generates
practice aimed at that specific gap.

Built for MGT 409. One model: `gpt-6-luna` via Portkey.

---

## Run it

Three commands. Tested from a fresh clone on Windows with Python 3.13.

```bash
pip install -r requirements.txt
python scripts/check_vision.py
streamlit run app/main.py
```

`check_vision.py` is one API call that confirms the model can read an image
and preserve Spanish diacritics. If it prints `VISION WORKS`, everything else
will run. The app opens at <http://localhost:8501>.

### Where it looks for your API key

`.env` in this repo folder first, then **one level above it**:

```
submissions/
├── .env              <-- found here if not in the repo
└── writing-coach/
    ├── .env          <-- checked first
    └── README.md
```

Only `PORTKEY_API_KEY` is needed. See `.env.example`. Verified working with
the key one level up and no `.env` inside the repo.

### Using it

Three views, in the sidebar.

**Assess** — enter a student name, upload page photos (several per
composition is fine) or pick a bundled sample. The page orientation is worked
out automatically; rotate buttons override it. **Transcribe**, read the
transcript against the image and correct anything misread, then **assess**.
Results appear in six tabs: FACT breakdown, targeted practice, a printable
sheet for the student, the full agent trace, guardrail status, and live token
cost. Everything is saved automatically.

**Progress** — one student across submissions: each criterion over time, and
whether the gap the app named actually closed. Try the seeded student
**Ana M.**

**History** — every saved assessment, filterable by student.

Worth trying: `hw_injection` is a real handwritten prompt-injection attempt,
and `hw_control` is the same text photographed sideways.

---

## The agents

```
image ──> Transcriber ──> transcript ──> [human confirms] ──┐
                                                            │
                        ┌────────┬───────────┬───────────┐  │
                        ▼        ▼           ▼           ▼  │
                     Eval F   Eval A      Eval C      Eval T│
                        └────────┴─────┬─────┴───────────┘  │
                                       ▼                    │
                                  Adjudicator               │
                                       ▼                    │
                                 DrillGenerator             │
                                       ▼                    │
                                   Verifier ◄───────────────┘
```

ACTFL assesses four independent criteria — Functions and tasks, Accuracy,
Context and content, Text type — and a writer can sit at different levels on
each. That spread *is* the diagnostic signal, because the weakest criterion is
what blocks the next sublevel. One agent asked for all four at once flattens
them toward a single impression, so each gets its own specialist.

That costs four times the calls. `scripts/compare_architectures.py` measures
exactly what collapsing them would save and what it would cost in agreement.

### Why the confirm step exists

Two measured failures. The transcriber read `entonces` as `entonses` and the
Accuracy evaluator cited the misreading as the student's spelling error. And
on an upside-down page it returned an *entirely invented composition* at 98%
confidence — fixed by giving it explicit permission to answer `[ilegible]`,
which it now does rather than guessing. The app also refuses to grade a page
it could not read.

A human still reads the transcript against the image before anything is
assessed, because a misread word becomes fabricated evidence.

### Guardrails

Three checks, all plain Python rather than prompts, because a guardrail
written as a prompt can be argued out of running:

| Check | What it stops |
|---|---|
| Injection scan | Instructions written *inside* the composition, in Spanish or English |
| Quote verification | Evidence quoting text that is not in the transcript |
| Over-claim scan | Prose asserting a certified ACTFL rating |

ACTFL requires sustained performance across many situations before a level can
be assigned (Guidelines 2024, p. 24). One sample cannot establish that, so the
app only ever reports evidence *consistent with* a level.

---

## Data

**Shipped with the repo** (`data/samples/`, `data/calibration/`) — eleven
small synthetic compositions, enough to run and demo everything including the
injection defence. Nothing to download.

**The validation set** is 18 real handwritten responses scored by College
Board AP readers. They are ~27 MB of College Board scans, so they are fetched
rather than committed:

```bash
python scripts/fetch_ap.py                   # download 6 PDFs from AP Central
python scripts/ingest_ap.py data/ap_pdfs/*.pdf
python scripts/rank_test.py                  # ~130 API calls, a few minutes
```

The app does not need any of this to run.

---

## Scripts

| Script | What it does |
|---|---|
| `check_vision.py` | Confirms the model reads images and keeps accents |
| `check_model_guard.py` | Fails if any model but `gpt-6-luna` appears |
| `build_rubric.py` | Rebuilds `rubric/actfl_writing.json` from the ACTFL PDF |
| `make_samples.py` | Regenerates the bundled demo compositions |
| `make_calibration_set.py` | Six compositions targeting known ACTFL sublevels |
| `run_sample.py` | Full pipeline on one sample, from the command line |
| `compare_architectures.py` | Four specialists vs one combined call: cost and agreement |
| `fetch_ap.py` / `ingest_ap.py` | Download and prepare the expert-scored set |
| `rank_test.py` | Rank agreement and calibration against AP scores |
| `aggregation_experiment.py` | Compares criterion-aggregation rules against both references |
| `abstention_experiment.py` | Whether the transcriber can be made to abstain rather than invent |
| `build_anchors.py` | Builds the (disabled) calibration anchors |
| `calibration_test.py` | Three-way: written target vs teacher's blind labels vs app |
| `seed_demo_history.py` | Seeds a worked example for the progress view |
| `build_report.py` / `build_slides.py` | Generate report.html and slides.html from measured results |
| `make_diagram.py` | Regenerates the architecture diagram |

Measured outputs land in `output/` as JSON.

---

## Model

`gpt-6-luna` through Portkey, named in `app/config.py` and nowhere else.
`python scripts/check_model_guard.py` fails the build if another identifier
appears anywhere in the repo.

Two gotchas carried over from Homework 5, both handled in
`backend/model_provider.py`:

- This family rejects `max_tokens`; it wants `max_completion_tokens`.
- `reasoning_effort` must be pinned to `'none'`, or the model spends its whole
  output budget reasoning and returns empty content.

---

## Credits

ACTFL Proficiency Guidelines 2024 © ACTFL, Inc., 2024 — descriptors quoted for
educational assessment. AP® sample responses and scoring © College Board;
fetched from AP Central, not redistributed here.
