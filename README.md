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

1. Pick a bundled sample in the sidebar, or upload a photo of handwriting.
2. **Transcribe**, then read the transcript against the image and correct it.
   This step is deliberately not skippable — see *Why the confirm step exists*.
3. **Assess**. Results appear in five tabs: FACT breakdown, targeted practice,
   the full agent trace, guardrail status, and live token cost.

Try `sample_05_injection` to watch the prompt-injection defence fire.

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

In testing, the transcriber read `entonces` as `entonses`, and the Accuracy
evaluator then cited the misreading as a student spelling error. The model
invented a mistake and graded it. A misread word becomes fabricated evidence,
so a human reads the transcript before anything is assessed.

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
