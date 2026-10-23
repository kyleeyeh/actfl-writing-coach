"""Central configuration.

Everything environment- or model-related lives here so there is exactly one
place to look. In particular: this project talks to exactly ONE model.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Repo root = the folder containing this app/ package.
ROOT = Path(__file__).resolve().parent.parent

# The assignment requires the app to find the key in two places: its own repo
# folder first, then the folder one level above (where the teaching staff keep
# their .env when every submission is cloned side by side). Order matters --
# a local .env wins, and load_dotenv does not overwrite what is already set.
load_dotenv(ROOT / ".env")
load_dotenv(ROOT.parent / ".env")

# --- Model -----------------------------------------------------------------
# The assignment permits exactly one model. Do not add others, do not fall
# back to another model on error, and do not import a model name from
# anywhere outside this file.
MODEL = "gpt-6-luna"

# This model family rejects `max_tokens` and requires `max_completion_tokens`.
# Passing the wrong one yields a confusing 400 from the Azure backend.
MAX_COMPLETION_TOKENS = 2000

PORTKEY_BASE_URL = "https://api.portkey.ai/v1"


def portkey_api_key() -> str:
    key = os.environ.get("PORTKEY_API_KEY")
    if not key:
        raise RuntimeError(
            "PORTKEY_API_KEY not found. Put it in .env in this repo folder, "
            "or in a .env one level above it (see .env.example)."
        )
    return key


# --- Paths -----------------------------------------------------------------
RUBRIC_DIR = ROOT / "rubric"
SAMPLES_DIR = ROOT / "data" / "samples"
OUTPUT_DIR = ROOT / "output"

# --- Spend guardrails ------------------------------------------------------
# Counted client-side; nothing is sent to the API. See backend/model_provider.
MAX_IMAGES_PER_SUBMISSION = 4
MAX_REQUESTS_PER_RUN = 12
