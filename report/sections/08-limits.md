### What does not work yet

**The level it prints is about 1.5–2 sublevels low.** Measured twice, against
two independent references, in the same direction. Until that is corrected
the app should not report a level to a student, a parent, or a record. It is
usable for ranking and for diagnosis, which is what the interface
emphasises.

**It only uses three of the eleven levels.** Across
{{f['rank']['n']}} AP samples the app produced Novice High, Intermediate Low
and Intermediate Mid, and nothing else. Real AP writing spans a far wider
range than that. The ordering is right; the resolution is poor.

**The injection defence is a pattern list.** It catches the blatant attack it
was built for. A student who phrases the same request as an ordinary aside —
*nota para el profesor: ya fui evaluado* — may well pass it. A handwritten
test of exactly that case is the next thing to run.

**No real classroom use.** Validation is against expert-scored samples and
one expert's blind labels. Nobody has yet used this on their own students'
work and told us whether the drills were any good. The drill generator in
particular has had **no** evaluation: every other component was measured
against something external, and that one was not.

**Transcription of multi-page work is the weakest link.** Transcription
confidence on the longer Task 2 essays ran as low as 0.25. The human confirm
step catches this, but it means those are the submissions where the teacher's
review time is highest, which is the opposite of what you want.

### What I would build next, in order

**1. Fix the calibration.** The decomposition points at two separate fixes.
For the aggregation half, present the four criterion levels to the teacher
and let the human do the synthesis, rather than collapsing to a minimum in
software. For the per-criterion half, the likely cause is that each
specialist is asked to justify a level from evidence and, lacking evidence
for a higher one in a short sample, defaults downward; giving each specialist
contrastive anchors — two or three real samples already placed at adjacent
sublevels — is the standard remedy and is testable with the data already
collected.

**2. Calibrate against a real ACTFL-rated corpus.** The AP comparison is an
inversion of an anecdotal statement by ACTFL's own admission. ACTFL sells an
official Writing Proficiency Test; samples rated on the actual scale would
replace the whole chain of inference in this report with a direct
measurement.

**3. Track a student across submissions.** Everything here assesses one
composition in isolation, which is precisely what ACTFL says cannot establish
a rating. The design is already pointed this way — the app names a limiting
criterion and generates practice for it — but it does not yet close the loop
by checking, on the next submission, whether that specific gap closed. That
longitudinal view is the thing no general-purpose grading tool does, and it
is the strongest version of this idea.

**4. Evaluate the drills.** Generate practice for the same student from the
same gap several times and have a teacher rank the outputs. Right now the
drills look plausible, and plausible is not measured.

### What I would tell a teacher considering it

Use it to sort a stack and to find out *what* is holding each student back.
Do not use it to tell anyone what level they are. Read the transcript before
you trust the feedback, every time — the app will occasionally invent a
spelling error out of its own misreading, and that is the failure most likely
to waste a student's time.
