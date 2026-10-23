# (working title) ACTFL Writing Coach

Photograph a student's handwritten Spanish composition. The app transcribes it
faithfully, reports which ACTFL 2024 Writing criteria the sample shows evidence
for, identifies the specific gap blocking the next sublevel, and generates
targeted practice aimed at that gap.

**Status: scaffold. Not yet runnable.**

## Quick start

```bash
python -m venv .venv && .venv/Scripts/activate   # Windows
pip install -r requirements.txt
cp .env.example .env            # then paste your PORTKEY_API_KEY
python scripts/check_vision.py  # confirms the model accepts image input
```

### Where the app looks for your key

`.env` in this repo folder first, then one level above it. Graders who clone
every submission side by side and keep a shared `.env` in the parent folder
need no changes.

## Model

Exactly one model: `gpt-6-luna` via Portkey. It is named in `app/config.py` and
nowhere else; `python scripts/check_model_guard.py` fails the build if another
identifier appears anywhere in the repo.

## Layout

| Path | What |
|---|---|
| `app/` | config + UI |
| `backend/` | agents, prompts, token accounting, guardrails |
| `rubric/actfl_writing.json` | ACTFL 2024 Writing descriptors, extracted from the official PDF |
| `data/samples/` | small test set so the app runs without private student work |
| `scripts/` | rubric builder, model guard, vision check |
| `report/`, `slides/` | deliverables |

## Rebuilding the rubric

```bash
python scripts/build_rubric.py path/to/ACTFL-Proficiency-Guidelines-2024.pdf
```

Descriptors are quoted from ACTFL Proficiency Guidelines 2024 (© ACTFL, Inc.,
2024) and used here for educational assessment.
