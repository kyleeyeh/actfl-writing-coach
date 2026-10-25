### What was measured, and what was not

The strongest evidence for a tool like this would be a teacher using it on
their own students' work for a term. That was not possible in the time
available, and this section does not pretend otherwise.

What *was* possible turned out to be better than a single pilot user: the
app was validated against **{{f['rank']['n']}} real handwritten compositions
scored by trained College Board AP readers**, and against **six compositions
labelled blind by a former Spanish teacher**. Both are expert judgements made
without reference to this app.

### Does it rank writing the way experts do?

AP scores are not ACTFL levels and no published conversion exists, so the
app's placements cannot be compared to AP scores directly. What can be
compared is the *ordering*: given writing that experts ranked, does the app
rank it the same way?

| | |
|---|---|
| Samples | {{f['rank_lang']['n']}} |
| Concordant pairs | {{f['rank_lang']['concordant']}} |
| Discordant pairs | **{{f['rank_lang']['discordant']}}** |
| Tied pairs | {{f['rank_lang']['tied']}} |
| Kendall tau-b | **{{"{:+.3f}".format(f['rank_lang']['tau_b'])}}** |

Against the teacher's blind labels, ordering agreement was stronger still:
tau-b **{{"{:+.3f}".format(f['calibration']['tau_teacher_vs_app'])}}**, with
zero discordant pairs.

So the app is tracking something real. When it says one composition is
stronger than another, experts agree — it almost never gets a pair backwards.

The weakness is visible in that tied count. {{f['rank_lang']['tied']}} of the
pairs are ties, because the app used only three distinct levels across all
{{f['rank']['n']}} AP samples. It discriminates reliably but coarsely.

### Does it assign the right level?

No. This is the clearest negative result in the project, and it replicates
across two independent references.

| reference | mean offset |
|---|---|
| Teacher's blind labels (well-formed items) | {{"{:+.2f}".format(f['calibration']['app_mean_offset'])}} sublevels |
| ACTFL's published AP comparison | −1.75 sublevels |

The app reads roughly one and a half to two sublevels below what an
experienced rater says, and the gap widens at higher proficiency.

A control in the calibration design shows where this comes from. The six
items were *written* to target specific sublevels before the teacher saw
them; on two of the six, the written target was itself two sublevels below
what the teacher called it. The item writer and the pipeline show the same
downward bias — so this is not a wiring fault, it is how a language model
reads the ACTFL descriptors.

The aggregation experiment splits it further: about 1.2 sublevels comes from
placing a writer at their weakest criterion, which compounds four separately
elicited conservative estimates; the remaining sublevel sits inside each
individual criterion judgement and cannot be aggregated away.

Two fixes were then attempted on that decomposition and both failed, which is
reported in Limits rather than omitted. Changing the aggregation rule helps
but is not defensible under ACTFL; injecting expert-labelled anchor
compositions closed a fifth of the gap while making ordering worse and
reintroducing fabricated quotes. The bias is real, measured, decomposed, and
still unfixed.

### So what is this actually worth today?

Stated conservatively, because the calibration result does not support a
stronger claim:

**Usable now.** Ranking a stack of compositions from strongest to weakest,
identifying which FACT criterion is holding a given student back, and
drafting targeted practice for it. Those depend on relative judgements and
on locating evidence in the text, both of which validated well.

**Not usable now.** Reporting a proficiency level to a student, a parent, or
a transcript. The app is measurably miscalibrated, by a known amount, in a
known direction.

**Time.** The pipeline runs in about 30 seconds per composition against the
10–15 minutes a proficiency-coded diagnosis takes by hand, but the honest
comparison is not 30 seconds against 15 minutes — it is *30 seconds plus
teacher review* against 15 minutes, and the review step has not been timed
with a stopwatch across a real stack of papers. Claiming a specific
multiplier without that measurement would be exactly the kind of unevidenced
number this report has tried to avoid.
