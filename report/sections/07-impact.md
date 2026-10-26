### A teacher using it on real, unseen work

The strongest available evidence for a tool like this is someone qualified
using it on work they have not seen before. That test was run.

A former high-school Spanish teacher was given a genuine College Board AP
Spanish Language email reply — real handwriting, not a fixture — with its
official score withheld. He read it and wrote down his own judgement
**before** the app was run on it: the level, the one thing he would tell the
student to work on, and how long it took him.

| | teacher | app |
|---|---|---|
| Level | Intermediate Mid | Intermediate **Low** |
| What to work on | subjunctive, *concordancia*, content specificity | same criterion, in more detail |
| Time | ~5 minutes | ~2 minutes |

Three things came out of five minutes of work, and the second is the most
useful.

**The level was one sublevel low, in exactly the predicted direction.** The
composition's official AP score is 3, and ACTFL's own published comparison
associates a 3 with Intermediate Mid. So the teacher matched the published
expectation precisely, and the app sat one rung beneath it — the same
direction, and roughly the same size, as the −1.5 sublevel bias measured
independently on 18 AP samples and on the six-item calibration set. A third
measurement of the same bias, from a different method.

**The diagnosis matched, and was more detailed than the human's.** The app
named the same limiting area the teacher did, and enumerated specific errors
he had summarised. In his words, this is where it earns its place: it *"can
point out specific errors really quickly."* That is the claim this project
most wanted tested, because diagnosis — not placement — is what the design is
built around.

**It was about twice as fast**, on one sample. That is a real number and a
small one; it is not a throughput study, and the teacher's own account of the
value was not speed but detail and targeting.

### What he said about using it

> I would definitely use this as a preliminary starting point, and I would
> even let my students play with it, telling it to trust its error spotting
> but defer to a conference with me for tailored coaching. The sample
> exercises are super targeted toward the gaps the student pointed out.

Note what that endorsement is careful about. It is a **first pass**, not a
verdict, and the student is told explicitly which part to trust. That is
almost exactly the division the measurements support — trust the error
spotting, do not trust the level — arrived at independently by someone using
the tool rather than reading its documentation.

### Validation against expert scores

Beyond the live test, the app was validated against **18 real handwritten
compositions scored by trained College Board AP readers**, and against six
compositions labelled blind by the same teacher.

**Does it rank writing the way experts do?** AP scores are not ACTFL levels
and no published conversion exists, so placements cannot be compared to AP
scores directly. Ordering can.

| | |
|---|---|
| Samples | {{f['rank_lang']['n']}} |
| Concordant pairs | {{f['rank_lang']['concordant']}} |
| Discordant pairs | **{{f['rank_lang']['discordant']}}** |
| Tied pairs | {{f['rank_lang']['tied']}} |
| Kendall tau-b | **{{"{:+.3f}".format(f['rank_lang']['tau_b'])}}** |

Against the teacher's blind labels, ordering agreement was stronger:
tau-b **{{"{:+.3f}".format(f['calibration']['tau_teacher_vs_app'])}}**, zero
discordant pairs. When the app says one composition is stronger than another,
experts agree; it almost never gets a pair backwards.

The weakness is in that tied count. {{f['rank_lang']['tied']}} of the pairs
are ties, because the app used only three distinct levels across all
{{f['rank']['n']}} AP samples. It discriminates reliably but coarsely.

**Does it assign the right level?** No — and this now replicates across three
independent references.

| reference | mean offset |
|---|---|
| Teacher's blind labels, six items | {{"{:+.2f}".format(f['calibration']['app_mean_offset'])}} sublevels |
| ACTFL's published AP comparison, 12 items | −1.75 sublevels |
| Teacher's live test, one unseen composition | −1 sublevel |

A control in the calibration design shows where this comes from. Two of the
six written items were themselves two sublevels below what the teacher called
them, so the item writer shows the same downward bias as the pipeline: this
is not a wiring fault, it is how a language model reads the ACTFL descriptors.

The aggregation experiment splits it further: about 1.2 sublevels comes from
placing a writer at their weakest criterion, which compounds four separately
elicited conservative estimates; the remaining sublevel sits inside each
individual criterion judgement.

Two fixes were then attempted on that decomposition and both failed, which is
reported in Limits rather than omitted. Changing the aggregation rule helps
but is not defensible under ACTFL; injecting expert-labelled anchor
compositions closed a fifth of the gap while making ordering worse and
reintroducing fabricated quotes. The bias is real, measured three ways,
decomposed — and still unfixed.

### So what is this actually worth today?

**Usable now, on a practising teacher's own account.** Ranking a stack from
strongest to weakest, finding which criterion is holding a student back, and
drafting targeted practice for it. All three depend on relative judgements
and on locating evidence in the text, both of which validated well, and all
three are what the teacher said he would use it for.

**Not usable now.** Reporting a proficiency level to a student, a parent or a
transcript. The app is miscalibrated by a known amount in a known direction,
and the interface says so where the teacher will see it.
