### What does not work yet

**The level it prints is about 1.5–2 sublevels low.** Measured twice, against
two independent references, in the same direction. Until it is corrected the
app should not report a level to a student, a parent or a record. The
interface says so on the results screen, and the student handout carries no
level at all.

Two fixes were attempted and both are recorded here as failures rather than
quietly dropped:

| attempt | effect on calibration | what it cost |
|---|---|---|
| Aggregate criteria by median instead of minimum | −1.75 → −1.33 | Not defensible under ACTFL, which places a writer where all criteria are *sustained* |
| Inject expert-labelled anchor compositions | −1.75 → −1.42 | Ordering worse (tau +0.459 → +0.432), discordant pairs 7 → 12, fabricated quotes 0 → 4 |

The anchor result is the more interesting failure. It closed about a fifth of
the gap and made everything else worse; the four fabrications were checked
against the anchor texts and did not come from them, so the mechanism was
simply a longer prompt making the evaluators less careful about quoting
verbatim. Trading ordering quality and quote fidelity for a small gain in a
number the app already tells people not to rely on is a bad trade, so anchors
are off by default with the flag and both result sets kept.

**It only uses three of the eleven levels.** Across 18 AP samples the app
produced Novice High, Intermediate Low and Intermediate Mid, and nothing else.
Real AP writing spans a far wider range. The ordering is right; the resolution
is poor, and that is what holds rank agreement at +0.46 — 101 of the 153 pairs
are ties.

**Skewed photographs still defeat it.** One of three real handwritten sheets
was both sideways and noticeably rotated off-square. The app now abstains
rather than inventing, which is the correct behaviour, but abstaining means
that page cannot be assessed without the teacher retyping it. Deskewing before
transcription is the obvious next step.

**The drill generator has never been evaluated.** Every other component was
measured against something external — expert AP scores, a teacher's blind
labels, known ground-truth text. The drills have been measured against
nothing. They look plausible. Plausible is not a measurement, and this is the
largest unexamined claim in the project.

**No classroom use.** Validation is against expert-scored samples and one
expert's blind labels. Nobody has used this on their own students' work over a
term and reported whether it helped.

### What I would build next, in order

**1. Deskew before transcription.** The cheapest remaining win. It directly
recovers the one sample the app currently refuses, and straighter lines should
help the transcriber everywhere.

**2. Calibrate against a real ACTFL-rated corpus.** The AP comparison is an
inversion of a statement ACTFL itself calls anecdotal. ACTFL sells an official
Writing Proficiency Test; samples rated on the actual scale would replace the
whole chain of inference in this report with a direct measurement. Both failed
fixes above were attempts to correct a bias measured through a proxy — which
may be part of why neither worked cleanly.

**3. Evaluate the drills.** Generate practice for the same gap several times
and have a teacher rank the outputs blind, the same design used for the
calibration set. Until that exists, the generated practice is the part of this
app a user should trust least.

**4. Close the loop properly.** The progress view shows whether a named gap
closed across submissions, but nothing yet checks whether the student actually
*did* the drill, or compares outcomes between gaps that were practised and
gaps that were not.

### Why the progress view is the most defensible part

Everything else assesses one composition, which is precisely what ACTFL says
cannot establish a rating. Several assessments over time are a different
claim, and the app's biggest weakness matters less to it: a roughly constant
bias largely cancels when you subtract two measurements taken the same way.
"Roughly" is carrying weight — the bias widens at higher proficiency, so gains
across that range are understated — but *did this student's bottleneck move?*
is a question this tool can already answer honestly, while *what level is this
student?* is one it cannot.

### What I would tell a teacher considering it

Use it to sort a stack and to find out *what* is holding each student back.
Do not use it to tell anyone what level they are. Read the transcript against
the page before you trust the feedback — the app will occasionally misread a
word and then grade the misreading, and that is the failure most likely to
waste a student's time.
