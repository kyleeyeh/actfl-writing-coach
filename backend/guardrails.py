"""Deterministic checks that run without a model.

A guardrail implemented as a prompt can be talked out of doing its job. These
cannot: they are string operations in Python, they run on every submission,
and they fail closed.

Three of them:

* `find_injection_attempts` -- scans the *transcript* for text addressed to
  the grading system rather than to the reader. The attack this project
  actually faces is a student writing an instruction inside the composition,
  which then arrives through OCR as ordinary input.

* `check_quotes` -- every piece of evidence claims a verbatim span. Here we
  simply check it is there. The verifier agent does this too; this version
  cannot be persuaded otherwise.

* `find_over_claims` -- flags prose that asserts a certified ACTFL rating,
  which a single sample can never support.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

# Phrases that address the system rather than the reader. Spanish and English,
# because a Spanish student writing an injection may well write it in Spanish.
INJECTION_PATTERNS = [
    r"ignor[ae]\s+(las\s+)?instruc",
    r"ignore\s+(the\s+|all\s+|previous\s+|prior\s+)*instruct",
    r"disregard\s+(the\s+|all\s+|previous\s+)*instruct",
    r"olvida\s+(todo|las\s+instruc)",
    r"dame\s+(un[ao]?\s+)?(nota|calificaci[oó]n|nivel)",
    r"give\s+me\s+(an?\s+)?(a\+?|advanced|superior|perfect|top)\b",
    r"\b(rate|grade|score|calif[ií]ca)\s+(me|this|esto)\b",
    r"system\s*prompt",
    r"you\s+are\s+now\b",
    r"act\s+as\b",
    r"act[uú]a\s+como\b",
    r"nuevas?\s+instrucciones",
    r"new\s+instructions",
]

# Wording that asserts a rating instead of reporting evidence.
OVER_CLAIM_PATTERNS = [
    r"\b(the\s+)?student\s+is\s+(a\s+)?(novice|intermediate|advanced|superior|distinguished)\b",
    r"\bis\s+rated\s+(novice|intermediate|advanced|superior|distinguished)\b",
    r"\bhas\s+achieved\s+(novice|intermediate|advanced|superior|distinguished)\b",
    r"\bofficial(ly)?\s+(rated|placed)\b",
    r"\bcertified\s+(as\s+)?(novice|intermediate|advanced|superior|distinguished)\b",
    r"\bproficiency\s+(level\s+)?is\s+(novice|intermediate|advanced|superior|distinguished)\b",
]


@dataclass
class InjectionHit:
    pattern: str
    excerpt: str


@dataclass
class QuoteCheck:
    quote: str
    found: bool
    criterion: str


def _normalise(text: str) -> str:
    """Fold case, accents and whitespace.

    Quote checking has to survive the transcript being retyped by a human in
    the confirm step, and injection detection has to survive a student writing
    IGNORA or Ignora or ignora. Accent folding also catches `calificacion`
    written without its accent, which a learner will very often do.
    """
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text).strip().lower()


def find_injection_attempts(transcript: str) -> list[InjectionHit]:
    flat = _normalise(transcript)
    hits: list[InjectionHit] = []
    for pat in INJECTION_PATTERNS:
        for m in re.finditer(pat, flat, flags=re.IGNORECASE):
            start = max(m.start() - 40, 0)
            end = min(m.end() + 40, len(flat))
            hits.append(InjectionHit(pattern=pat, excerpt=flat[start:end]))
    return hits


def check_quotes(transcript: str, findings) -> list[QuoteCheck]:
    """Verify every claimed quote really appears in the transcript."""
    haystack = _normalise(transcript)
    out: list[QuoteCheck] = []
    for f in findings:
        for e in f.evidence:
            needle = _normalise(e.quote)
            out.append(
                QuoteCheck(
                    quote=e.quote,
                    found=bool(needle) and needle in haystack,
                    criterion=f.criterion,
                )
            )
    return out


def find_over_claims(*texts: str) -> list[str]:
    hits: list[str] = []
    for text in texts:
        if not text:
            continue
        # Sentence-ish split; good enough to quote the offending clause back.
        for sentence in re.split(r"(?<=[.!?])\s+", text):
            flat = _normalise(sentence)
            if any(re.search(p, flat) for p in OVER_CLAIM_PATTERNS):
                hits.append(sentence.strip())
    return hits
