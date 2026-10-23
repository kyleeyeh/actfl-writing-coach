"""Does gpt-6-luna accept image input through Portkey?

The whole project ingests photographed handwriting, so this is the one
assumption worth testing before building anything on top of it. Run it first:

    python scripts/check_vision.py

It renders a tiny image containing accented Spanish text, sends it as a base64
data URL, and reports whether the model read it back. One API call.

Exit 0 = vision works. Exit 1 = it does not, and the ingestion plan must change.
"""

import base64
import io
import json
import sys
from pathlib import Path

# Windows consoles default to cp1252, which cannot print the accented Spanish
# this project exists to handle. Without this, correct output crashes the
# script on a print() -- a confusing failure that looks like a model problem.
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont

from app.config import MODEL, PORTKEY_BASE_URL, portkey_api_key

# Accents and an inverted mark: exactly the characters that general OCR drops,
# and exactly the ones that carry the Accuracy signal we grade on.
PHRASE = "¿Adónde fuiste ayer? Mi mamá compró el pañuelo."


def _font() -> ImageFont.FreeTypeFont:
    """A real TrueType face.

    PIL's built-in bitmap font has no glyphs for the characters this project
    cares about most -- it silently draws blanks for the inverted mark and
    several accented vowels. Testing accent fidelity with it measures the
    font, not the model.
    """
    for name in ("segoeui.ttf", "arial.ttf", "calibri.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, 34)
        except OSError:
            continue
    raise RuntimeError("No TrueType font found; cannot render an honest test image.")


def make_image() -> str:
    img = Image.new("RGB", (760, 110), "white")
    ImageDraw.Draw(img).text((20, 30), PHRASE, fill="black", font=_font())
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    # Keep the rendered image so it can be eyeballed when a run looks wrong.
    probe = Path(__file__).resolve().parent.parent / "output" / "vision_probe.png"
    probe.parent.mkdir(parents=True, exist_ok=True)
    probe.write_bytes(buf.getvalue())
    return base64.b64encode(buf.getvalue()).decode()


def main() -> int:
    client = OpenAI(base_url=PORTKEY_BASE_URL, api_key=portkey_api_key(), timeout=90.0)

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Transcribe the text in this image exactly, "
                            "preserving every accent and punctuation mark. "
                            "Reply with the transcription only.",
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{make_image()}"
                            },
                        },
                    ],
                }
            ],
            # NOT max_tokens -- this model family rejects it with a confusing 400.
            max_completion_tokens=600,
            # Without this the model spends the whole output budget on reasoning
            # tokens and returns empty content. Mirrors the pin in
            # backend/model_provider.py.
            reasoning_effort='none',
        )
    except Exception as exc:  # noqa: BLE001 -- we want the raw provider message
        print("VISION UNAVAILABLE")
        print(f"  {type(exc).__name__}: {exc}")
        print("\nIngestion must change: typed-text input, or a separate OCR step.")
        return 1

    got = (resp.choices[0].message.content or "").strip()
    usage = resp.usage

    if not got:
        print("INCONCLUSIVE -- call succeeded but content was empty")
        print(f"  usage: {usage}")
        print("  Usually means the output budget went to reasoning tokens.")
        return 1

    print("VISION WORKS")
    print(f"  model returned : {resp.model}")
    print(f"  sent           : {PHRASE}")
    print(f"  read back      : {got}")
    if usage:
        print(
            f"  tokens         : in={usage.prompt_tokens} "
            f"out={usage.completion_tokens} total={usage.total_tokens}"
        )

    # Accent fidelity is the thing that actually matters, not a perfect match.
    missed = [c for c in "¿áóñ" if c in PHRASE and c not in got]
    if missed:
        print(f"  WARNING: dropped characters {missed} -- accents are not safe.")
    else:
        print("  accents       : all preserved")

    # Written as UTF-8 so the result survives any console encoding, and so the
    # token counts can be quoted in the Tokenomics section.
    out = Path(__file__).resolve().parent.parent / "output" / "vision_check.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "model": resp.model,
        "sent": PHRASE,
        "read_back": got,
        "accents_dropped": missed,
        "prompt_tokens": usage.prompt_tokens if usage else None,
        "completion_tokens": usage.completion_tokens if usage else None,
        "total_tokens": usage.total_tokens if usage else None,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  saved         : {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
