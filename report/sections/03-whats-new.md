### What already exists

The AI-grades-writing space is crowded, and it would be dishonest to pretend
otherwise. The tools a Spanish teacher would plausibly reach for today:

| Tool | What it does | What it does not do here |
|---|---|---|
| **MagicSchool AI** | Teacher-facing suite; rubric-based feedback generators | Typed input; a rubric you paste, not a proficiency standard applied criterion by criterion |
| **Brisk Teaching** | Browser extension; feedback and grading inside Google Docs | Assumes the work is already a Google Doc — i.e. already typed |
| **Writable** | Assignment and feedback platform with rubric scoring | Built around English-language writing instruction, typed |
| **Turnitin Revision Assistant** | Formative feedback against rubric traits | Typed submissions; English |
| **Grammarly / general LLM chat** | Corrects errors fluently | *Corrects* — which destroys the evidence a proficiency assessment is made of |
| **ACTFL Writing Proficiency Test** | The official, human-rated instrument | Accurate and authoritative, but costs money per test and returns a rating, not a diagnosis or practice |

And the obvious one: a teacher can paste a composition into ChatGPT with the
ACTFL guidelines and ask for an assessment. That works, roughly, and is the
real competitor.

### What is different

**It reads paper.** Every tool above assumes typed input. Language teachers
collect handwriting on purpose, because a keyboard supplies the accents and
the autocorrect that the student is supposed to be demonstrating. This is the
only one of these that starts from a photograph of the page.

**It transcribes diplomatically.** The transcription step is explicitly
instructed to preserve every spelling error, missing accent and wrong verb
form. Every general tool does the opposite — it tidies. Tidying is correct
behaviour for a writing assistant and fatal for an assessment, because the
errors *are* the measurement. This is also the hardest part to get right:
see Safety for a case where the transcriber introduced an error that was then
graded as the student's.

**It separates the four ACTFL criteria instead of giving one impression.** A
writer can be Intermediate Mid on Accuracy and Novice High on Text Type, and
that gap is the entire diagnostic value — it says *you write correct
sentences but never link them into a paragraph*. A single model asked for one
overall judgement flattens exactly the signal a teacher needs.

**It names the blocking criterion and generates practice for that.** Not
general review: the limiting criterion drives the drill generator, so a
student weak on Text Type gets sentence-combining work rather than another
vocabulary list.

**It refuses to over-claim.** ACTFL is explicit that a rating requires
sustained performance across many situations. Ask ChatGPT to rate a
composition and it will tell you a level. This app reports evidence
*consistent with* a level and has a guardrail that scans its own output for
sentences asserting otherwise. That is a worse user experience and a more
honest one.

### Where the comparison is unflattering

A general LLM given the guidelines and a typed composition will produce
feedback that reads about as well as this app's, in one call, for a fifth of
the cost. The things this project adds — paper input, diplomatic
transcription, criterion separation, quote verification, calibration
measurement — are infrastructure around that call, not a better call. Whether
that infrastructure is worth building is exactly what the validation sections
are for, and the answer there is mixed: the ordering validates, the absolute
calibration does not.
