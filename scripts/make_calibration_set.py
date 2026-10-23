"""Six synthetic compositions, written to target different ACTFL sublevels.

WHAT THIS IS FOR
----------------
The AP samples validate the app against expert scores, but AP scores are not
ACTFL levels, so they can only confirm the ORDER the app puts samples in. They
cannot confirm that the level it prints is the right level.

This set attacks that directly. Six short compositions on one topic, each
written to sit at a specific ACTFL sublevel. Three independent judgements are
then compared:

    1. the level each was WRITTEN to target,
    2. the level a former Spanish teacher assigns, reading them blind,
    3. the level the app reports.

Where all three agree, the app is calibrated. Where (1) and (2) agree but (3)
differs, the app is off. Where (1) and (2) disagree, the targets were badly
written and the item is discarded rather than counted.

The letters A-F are deliberately NOT in level order, and the key lives in a
separate file so the texts can be read without seeing the answers.

    python scripts/make_calibration_set.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "calibration"

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

PROMPT_ES = (
    "Preséntate. Escribe sobre dónde vives, cuántos años tienes, cómo eres "
    "(físicamente y de personalidad), tu familia y tus amigos, y lo que te "
    "gusta y no te gusta."
)

# Letters are shuffled with respect to level on purpose.
ITEMS = [
    {
        "id": "A",
        "target": "Intermediate Mid",
        "text": (
            "Me llamo Santiago, tengo diecisiete años y vivo en Denver, "
            "Colorado. Soy una persona tranquila y paciente, aunque mis "
            "amigos dicen que hablo demasiado cuando estoy nervioso. Vivo "
            "con mis padres y mi hermano menor, que tiene nueve años y "
            "siempre quiere jugar conmigo. Me encanta tocar la guitarra y "
            "los fines de semana practico con mi mejor amigo Tomás, que es "
            "muy divertido. No me gusta levantarme temprano, pero el año "
            "pasado empecé a correr por las mañanas."
        ),
    },
    {
        "id": "B",
        "target": "Novice Mid",
        "text": (
            "Hola. Me llamo Diego. Yo tengo 16 anos. Mi casa es en Chicago. "
            "Me gusta futbol y pizza."
        ),
    },
    {
        "id": "C",
        "target": "Advanced Low",
        "text": (
            "Me llamo Nicolás, tengo dieciocho años y vivo en Austin, aunque "
            "nací en Monterrey y pasé allí los primeros seis años de mi "
            "vida. Siempre me han descrito como alguien observador y "
            "testarudo: cuando me propongo algo, no lo suelto hasta "
            "terminarlo, lo cual a veces frustra a mi madre. Mi familia es "
            "pequeña pero unida; mi padre trabaja como mecánico, mi madre es "
            "enfermera, y los tres cenamos juntos casi todas las noches. "
            "Antes prefería pasar el tiempo solo, pero desde que entré al "
            "equipo de debate he hecho amigos que me han cambiado bastante, "
            "sobre todo Rafael, que es el más leal que conozco. No soporto "
            "la impuntualidad ni las conversaciones superficiales, mientras "
            "que disfruto muchísimo leer novelas policiacas y discutirlas "
            "con quien quiera escucharme."
        ),
    },
    {
        "id": "D",
        "target": "Intermediate Low",
        "text": (
            "Me llamo Andrés y tengo dieciséis años. Vivo en una casa "
            "pequeña en Phoenix con mi mamá, mi papá y mi hermana. Mi "
            "hermana se llama Lucía y ella es muy comica pero a veces es "
            "molestosa. Yo soy alto y delgado, y mis amigos dicen que soy "
            "generoso. Me gusta mucho el basquetbol pero no me gustan las "
            "matematicas."
        ),
    },
    {
        "id": "E",
        "target": "Novice High",
        "text": (
            "Hola, me llamo Mateo y tengo quince años. Yo vivo en Houston "
            "con mi familia. Mi madre es simpatica y mi padre es alto. Me "
            "gusta jugar videojuegos y escuchar musica. No me gusta la "
            "tarea."
        ),
    },
    {
        "id": "F",
        "target": "Intermediate High",
        "text": (
            "Me llamo Emilio y tengo diecisiete años; vivo en las afueras de "
            "Seattle desde que mi familia se mudó allí hace seis años. Soy "
            "bastante reservado al principio, pero cuando conozco bien a "
            "alguien me vuelvo hablador y bromista. En mi casa somos cuatro: "
            "mis padres, mi hermana mayor Valentina, que estudia enfermería, "
            "y yo. Lo que más me gusta es cocinar con mi abuela, porque ella "
            "me enseña recetas que aprendió en México cuando era niña. "
            "Aunque antes odiaba la clase de historia, este año la encuentro "
            "interesante y creo que voy a estudiar algo relacionado."
        ),
    },
]


def font(size: int) -> ImageFont.FreeTypeFont:
    for name in ("segoeui.ttf", "arial.ttf", "calibri.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    raise RuntimeError("No TrueType font available.")


def wrap(text: str, draw: ImageDraw.ImageDraw, f, width: int) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=f) <= width:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def render(item: dict) -> Path:
    f = font(30)
    margin, width = 50, 940
    scratch = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    lines = wrap(item["text"], scratch, f, width - 2 * margin)

    img = Image.new("RGB", (width, margin * 2 + len(lines) * 44 + 30), "#fdfdf7")
    d = ImageDraw.Draw(img)
    d.text((margin, margin - 18), f"Muestra {item['id']}", fill="#555", font=font(20))
    for i, line in enumerate(lines):
        d.text((margin, margin + 22 + i * 44), line, fill="#1a1a2e", font=f)

    path = OUT / f"calib_{item['id']}.png"
    img.save(path)
    return path


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    # Readable texts, no levels: this is what the teacher marks up.
    sheet = [f"PROMPT: {PROMPT_ES}", ""]
    for it in ITEMS:
        render(it)
        sheet += [
            f"--- Muestra {it['id']} " + "-" * 50,
            it["text"],
            "",
            "   your ACTFL level: ______________________",
            "",
        ]
    (OUT / "blind_sheet.txt").write_text("\n".join(sheet), encoding="utf-8")

    # Public manifest: no targets in it.
    (OUT / "manifest.json").write_text(
        json.dumps(
            {
                "prompt_es": PROMPT_ES,
                "samples": [
                    {"id": it["id"], "file": f"calib_{it['id']}.png"} for it in ITEMS
                ],
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    # The answers, kept apart so the sheet can be read without them.
    (OUT / "TARGETS_DO_NOT_READ_FIRST.json").write_text(
        json.dumps(
            {it["id"]: it["target"] for it in ITEMS}, indent=2, ensure_ascii=False
        ),
        encoding="utf-8",
    )

    print(f"{len(ITEMS)} items written to {OUT}")
    print("  blind_sheet.txt                 <- read and label this")
    print("  TARGETS_DO_NOT_READ_FIRST.json  <- the answers; open afterwards")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
