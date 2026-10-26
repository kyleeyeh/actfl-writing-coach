**Entrenador de escritura** (ACTFL Writing Coach) — reads a photograph of a student's handwritten
Spanish, reports which ACTFL 2024 Writing criteria the sample shows evidence
for, names the one criterion blocking the next sublevel, and generates
practice aimed at that specific gap.

| | |
|---|---|
| Author | Kyle Yeh |
| Course | MGT 409, AI Foundations for Managers |
| Repository | https://github.com/kyleeyeh/actfl-writing-coach |
| Running the app | `pip install -r requirements.txt` then `streamlit run app/main.py`; see README |
| Model | `gpt-6-luna` via Portkey, one model, no fallback |

! **The short version.** The app ranks student writing the way expert raters
do — tau-b {{"{:+.2f}".format(f['rank_lang']['tau_b'])}} against
{{f['rank_lang']['n']}} College Board AP-scored handwritten samples, with
only {{f['rank_lang']['discordant']}} discordant pairs, and
{{"{:+.2f}".format(f['calibration']['tau_teacher_vs_app'])}} against a former
Spanish teacher's blind labels with none. It does **not** yet assign the
right absolute level: it reads about 1.5 to 2 ACTFL sublevels low, measured
independently against both references. Diagnosis works; certification does
not. This report explains how both were measured and where the bias comes
from.
